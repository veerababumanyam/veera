"""Audited count adapters; frozen commands and acceptance remain authoritative."""
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import time
import uuid


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_pin(root, ref):
    require(isinstance(ref, dict) and set(ref) == {'path', 'sha256'}, 'Use exact evidence pin fields')
    name = ref['path']
    require(isinstance(name, str) and name and '\\' not in name and ':' not in name,
            'Evidence needs a canonical task-relative path')
    parts = PurePosixPath(name).parts
    require(not name.startswith('/') and name == '/'.join(parts) and '..' not in parts,
            'Evidence path escapes task')
    require(not any(p.lower() in ('.git', '.veera', '.codex', '.claude', 'credentials.json', 'id_rsa', 'id_ed25519')
                    or p.lower().startswith('.env') for p in parts), 'Protected evidence path')
    root = Path(root).resolve()
    path = root
    for part in parts:
        path = path / part
        require(not path.is_symlink() and not getattr(path, 'is_junction', lambda: False)(), 'Linked evidence is not supported')
        require(not path.is_dir() or not (path / '.git').exists(), 'Evidence belongs to a nested project')
    require(path.resolve().is_relative_to(root) and path.is_file(), 'Missing task evidence')
    require(isinstance(ref['sha256'], str) and re.fullmatch('[0-9a-f]{64}', ref['sha256']), 'Invalid evidence hash')
    with path.open('rb') as stream:
        data = stream.read(8 * 1024 * 1024 + 1)
    require(0 < len(data) <= 8 * 1024 * 1024, 'Empty or oversized evidence')
    require(hashlib.sha256(data).hexdigest() == ref['sha256'], 'Pinned evidence changed: ' + name)
    return data


def command_inputs(spec):
    """Only the existing narrow Python verifier invocation can be rebound."""
    require(spec['kind'] == 'test', 'Only test verifier inputs are supported')
    argv = spec['argv']
    require(argv.count('verify') == 1, 'Frozen command must invoke the pinned verifier')
    index = argv.index('verify')
    require(index in (2, 3) and (index != 3 or argv[1] == '-B')
            and Path(argv[0]).is_absolute() and re.fullmatch(r'python(?:3(?:\.\d+)?)?(?:\.exe)?', Path(argv[0]).name.lower()),
            'Unsupported frozen verifier invocation')
    require(len(argv) == index + 5 and argv[index + 1] == '--manifest' and argv[index + 3] == '--results',
            'Unsupported frozen verifier inputs')
    return {'verifier': argv[index - 1], 'manifest': argv[index + 2], 'results': argv[index + 4]}


def validate(root, spec, adapter):
    """Derive cardinality only; the unchanged verifier validates every row."""
    require(isinstance(adapter, dict) and set(adapter) == {'kind', 'verifier', 'manifest', 'results'}
            and adapter['kind'] == 'verified-json-matrix', 'Unsupported reporting adapter')
    data = {key: read_pin(root, adapter[key]) for key in ('verifier', 'manifest', 'results')}
    require(len({adapter[key]['path'] for key in data}) == 3, 'Evidence pins must be distinct')
    require(command_inputs(spec) == {key: adapter[key]['path'] for key in data},
            'Adapter must bind the exact frozen verifier inputs')
    manifest, results = (json.loads(data[key]) for key in ('manifest', 'results'))
    require(isinstance(manifest, dict) and isinstance(results, dict), 'Expected matrix objects')
    campaign = manifest.get('campaign_id')
    require(isinstance(campaign, str) and campaign and results.get('campaign_id') == campaign
            and results.get('live') is True, 'Expected matching live campaign')
    engines, cases, repetitions = (manifest.get(key) for key in ('engines', 'concurrencies', 'repetitions'))
    require(isinstance(engines, list) and engines and all(isinstance(x, str) and x for x in engines)
            and len(set(engines)) == len(engines), 'Invalid engine matrix')
    require(isinstance(cases, list) and cases and all(type(x) is int and x > 0 for x in cases)
            and len(set(cases)) == len(cases), 'Invalid concurrency matrix')
    require(type(repetitions) is int and repetitions > 0, 'Invalid repetition count')
    cardinality = len(engines) * len(cases) * repetitions
    require(cardinality <= 100000, 'Matrix too large')
    runs = results.get('runs')
    require(isinstance(runs, list) and len(runs) == cardinality, 'Incomplete matrix')
    keys = []
    for row in runs:
        require(isinstance(row, dict) and isinstance(row.get('engine'), str)
                and type(row.get('concurrency')) is int and type(row.get('repetition')) is int,
                'Invalid matrix row identity')
        keys.append((row['engine'], row['concurrency'], row['repetition']))
    expected = Counter((engine, case, repetition) for engine in engines for case in cases for repetition in range(repetitions))
    require(Counter(keys) == expected, 'Missing, duplicated or extra matrix rows')
    return {'count': cardinality, 'campaign_id': campaign,
            'artifacts': {adapter[key]['path']: adapter[key]['sha256'] for key in data}}


def selected(state, spec, digest):
    receipts = [receipt for receipt in state.get('reporting_corrections', []) if receipt['report']['check_id'] == spec['id']]
    if not receipts:
        return None
    receipt = receipts[-1]
    require(receipt['report']['expected_check_hash'] == digest(spec), 'Corrected check specification changed')
    return receipt


def rebind(root, report, d):
    fields = {'run_id', 'checkpoint_id', 'expected_contract_hash', 'check_id', 'expected_check_hash',
              'expected_checks_hash', 'authorization_id', 'authorization', 'reason',
              'verifier', 'prior_inputs', 'inputs', 'review'}
    require(isinstance(report, dict) and set(report) == fields, 'Use exact check-input rebinding fields')
    for key in fields - {'verifier', 'prior_inputs', 'inputs', 'review'}:
        require(isinstance(report[key], str) and report[key].strip(), 'Nonempty ' + key + ' required')
    for key in ('prior_inputs', 'inputs'):
        require(isinstance(report[key], dict) and set(report[key]) == {'manifest', 'results'}, 'Use exactly manifest and results pins')
    with d.locked(root) as directory:
        state = d.load(directory)
        d.recovery_identity(root, state, report)
        require(state['repairs'] < d.repair_limit(state), 'Repair allowance exhausted')
        require(not any(r['report']['authorization_id'] == report['authorization_id'] for r in state.get('input_rebindings', [])),
                'Input rebinding authorization already applied')
        spec = next((c for c in state['contract']['checks'] if c['id'] == report['check_id']), None)
        require(spec and d.digest(spec) == report['expected_check_hash'], 'Stale check specification')
        require(d.digest(state['checks']) == report['expected_checks_hash'], 'Check results changed')
        require(selected(state, spec, d.digest) is None, 'Cannot rebind a reporting-corrected check')
        previous = state['checks'].get(spec['id'])
        require(not previous or previous.get('status') != 'failed'
                or (type(previous.get('repair_attempt')) is int and previous['repair_attempt'] < state['repairs']),
                'Record a bounded repair after the failed check before rebinding')
        paths = command_inputs(spec)
        require(report['verifier']['path'] == paths['verifier'], 'Verifier path cannot change')
        read_pin(root, report['verifier'])
        require(paths['verifier'] in d.snapshot(root), 'Verifier must be part of checkpointed source')
        validate_bindings(root, state, spec, d.digest)
        occupied = {(Path(root) / paths['verifier']).resolve()}
        for key in ('manifest', 'results'):
            require(report['prior_inputs'][key]['path'] == paths[key], 'Prior input differs from frozen argument')
            read_pin(root, report['prior_inputs'][key])
            occupied.add((Path(root) / paths[key]).resolve())
        # No historical target (even an earlier generation) may be overwritten
        # or selected as a new destination. Every pin remains resolvable.
        for receipt in state.get('input_rebindings', []):
            for pins in ('prior_inputs', 'inputs'):
                occupied.update((Path(root) / pin['path']).resolve() for pin in receipt['report'][pins].values())
        for key in ('manifest', 'results'):
            pin = report['inputs'][key]
            read_pin(root, pin)
            path = (Path(root) / pin['path']).resolve()
            require(path not in occupied, 'New inputs require distinct, previously unused paths')
            occupied.add(path)
        updated = copy.deepcopy(spec)
        updated['argv'][-3] = report['inputs']['manifest']['path']
        updated['argv'][-1] = report['inputs']['results']['path']
        adapter = {'kind': 'verified-json-matrix', 'verifier': report['verifier'], **report['inputs']}
        observation = validate(root, updated, adapter)
        review = report['review']
        binding = {key: report[key] for key in ('verifier', 'prior_inputs', 'inputs')}
        require(isinstance(review, dict) and set(review) == {'reviewer', 'notes', 'approved', 'fingerprint',
                'prior_check_hash', 'new_check_hash', 'binding_hash'} and review['approved'] is True
                and isinstance(review['reviewer'], str) and review['reviewer'].strip()
                and isinstance(review['notes'], str) and review['notes'].strip()
                and review['fingerprint'] == state['checkpoint']['fingerprint']
                and review['prior_check_hash'] == d.digest(spec) and review['new_check_hash'] == d.digest(updated)
                and review['binding_hash'] == d.digest(binding), 'Independent input-equivalence review is stale or missing')
        contract = copy.deepcopy(state['contract'])
        contract['checks'] = [updated if c['id'] == spec['id'] else c for c in contract['checks']]
        d.validate_contract(contract, root)
        receipt = {'id': uuid.uuid4().hex, 'at': time.time(), 'report': report, 'prior_check': spec,
                   'new_check': updated, 'prior_contract': state['contract'], 'prior_contract_hash': state['contract_hash'],
                   'contract_hash': d.digest(contract), 'prior_checks': state['checks'], 'prior_review': state.get('review'),
                   'observation': observation}
        state.setdefault('input_rebindings', []).append(receipt)
        state['contract'] = contract
        state['contract_hash'] = receipt['contract_hash']
        state['checks'] = {}
        state['review'] = None
        d.event(state, 'rebind-check-inputs', receipt)
        d.save(directory, state)
        return state


def validate_bindings(root, state, spec, digest):
    """Check new evidence and every original input without executing old builds."""
    receipts = [r for r in state.get('input_rebindings', []) if r['report']['check_id'] == spec['id']]
    if not receipts:
        return None
    previous = None
    for receipt in receipts:
        require(previous is None or receipt['prior_check'] == previous, 'Broken input rebinding history')
        for pin in receipt['report']['prior_inputs'].values():
            read_pin(root, pin)
        previous = receipt['new_check']
    latest = receipts[-1]
    require(digest(spec) == digest(latest['new_check']), 'Rebound check specification changed')
    adapter = {'kind': 'verified-json-matrix', 'verifier': latest['report']['verifier'], **latest['report']['inputs']}
    observation = validate(root, spec, adapter)
    return latest, observation


def correct(root, report, d):
    fields = {'run_id', 'checkpoint_id', 'expected_contract_hash', 'check_id', 'expected_check_hash',
              'expected_result_hash', 'log_sha256', 'authorization_id', 'authorization', 'reason', 'adapter', 'review'}
    require(isinstance(report, dict) and set(report) == fields, 'Use exact reporting-correction fields')
    for key in fields - {'adapter', 'review'}:
        require(isinstance(report[key], str) and report[key].strip(), 'Nonempty ' + key + ' required')
    with d.locked(root) as directory:
        state = d.load(directory)
        d.recovery_identity(root, state, report)
        require(state['repairs'] < d.repair_limit(state), 'Repair allowance exhausted')
        require(not any(r['report']['authorization_id'] == report['authorization_id'] for r in state.get('reporting_corrections', [])),
                'Reporting authorization already applied')
        spec = next((c for c in state['contract']['checks'] if c['id'] == report['check_id']), None)
        require(spec and d.digest(spec) == report['expected_check_hash'], 'Stale check specification')
        validate_bindings(root, state, spec, d.digest)
        result = state['checks'].get(spec['id'])
        require(result and d.digest(result) == report['expected_result_hash'], 'Stale failed result')
        require(result.get('status') == 'failed' and result.get('exit_code') == 0 and result.get('test_count') == 0
                and result.get('reason') == '' and result.get('argv') == spec['argv']
                and result.get('fingerprint') == state['checkpoint']['fingerprint'], 'Failure is not isolated to counting')
        require(type(result.get('repair_attempt')) is int and result['repair_attempt'] < state['repairs'],
                'Record a bounded repair after the failed check before correction')
        log_name = result.get('log', '')
        require(isinstance(log_name, str) and re.fullmatch(re.escape(spec['id']) + r'-[0-9a-f]{32}\.log', log_name), 'Invalid failed log identity')
        log = directory / log_name
        require(log.is_file() and not log.is_symlink() and hashlib.sha256(log.read_bytes()).hexdigest() == report['log_sha256'],
                'Failed log changed')
        observation = validate(root, spec, report['adapter'])
        require(report['adapter']['verifier']['path'] in d.snapshot(root), 'Verifier must be part of checkpointed source')
        review = report['review']
        require(isinstance(review, dict) and set(review) == {'reviewer', 'notes', 'approved', 'fingerprint', 'check_hash', 'adapter_hash'}
                and review['approved'] is True and isinstance(review['reviewer'], str) and review['reviewer'].strip()
                and isinstance(review['notes'], str) and review['notes'].strip()
                and review['fingerprint'] == state['checkpoint']['fingerprint']
                and review['check_hash'] == d.digest(spec) and review['adapter_hash'] == d.digest(report['adapter']),
                'Independent equivalence review must bind current source, check and adapter')
        receipt = {'id': uuid.uuid4().hex, 'at': time.time(), 'report': report, 'prior_check': spec,
                   'prior_result': result, 'prior_count_pattern': spec['count_pattern'], 'observation': observation}
        state.setdefault('reporting_corrections', []).append(receipt)
        state['checks'] = {}
        state['review'] = None
        d.event(state, 'correct-check-reporting', receipt)
        d.save(directory, state)
        return state


def validate_result(root, state, spec, result, digest):
    binding = validate_bindings(root, state, spec, digest)
    if binding:
        receipt, observation = binding
        require(result.get('input_rebinding_id') == receipt['id']
                and all(result.get('artifacts', {}).get(path) == sha for path, sha in observation['artifacts'].items()),
                'Missing or stale rebound check evidence')
    receipt = selected(state, spec, digest)
    if receipt:
        observed = validate(root, spec, receipt['report']['adapter'])
        require(result.get('reporting_correction_id') == receipt['id']
                and result.get('count_source') == 'verified-json-matrix'
                and result.get('test_count') == observed['count']
                and result.get('artifacts') == observed['artifacts'], 'Missing or stale corrected check evidence')
