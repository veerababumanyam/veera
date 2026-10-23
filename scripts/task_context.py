"""Task-local shared context and bounded blocker ledger; no external storage."""
import copy
import hashlib
from pathlib import Path
import re
import time
import uuid

import delivery as d

HUMAN = {'permission', 'authentication', 'human-decision'}
FAMILIES = HUMAN | {'test', 'build', 'dependency', 'integration', 'runtime', 'requirement'}


def text(value, limit=2000):
    d.require(isinstance(value, str) and 0 < len(value.strip()) <= limit, 'Expected nonempty bounded text')
    d.require(not re.search(r'-----BEGIN .*PRIVATE KEY|\b(?:ghp_|sk-ant-)[A-Za-z0-9_-]+', value), 'Do not store credentials in task memory')
    return value


def source(root, record):
    name = text(record.get('path'), 500)
    relative = Path(name)
    d.require(not relative.is_absolute() and '..' not in relative.parts, 'Sources must be task-relative')
    d.require(not any(p in ('.git', '.ssh', 'credentials.json', 'id_rsa', 'id_ed25519') or p.startswith('.env') for p in relative.parts), 'Sensitive source path refused')
    path = (Path(root) / name).resolve()
    d.require(path.is_relative_to(Path(root).resolve()) and path.is_file(), 'Source missing or outside task')
    d.require(path.stat().st_size <= 8 * 1024 * 1024, 'Source too large for context hashing')
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    d.require(record.get('sha256') == sha, 'Source hash changed: ' + name)
    return {'path': name, 'sha256': sha}


def sources(root, records):
    d.require(isinstance(records, list) and 0 < len(records) <= 10, 'Evidence needs 1–10 source references')
    return [source(root, item) for item in records]


def unresolved(state):
    return [b['id'] for b in state.get('blockers', {}).values() if b['status'] != 'resolved']


def require_clear(state):
    d.require(not state.get('repair_escalation') or state.get('repair_escalation_decision'), 'Repair escalation requires an evidence-backed PM/Architect/Advisor decision')
    d.require(not unresolved(state), 'Unresolved blockers prevent completion/publication: ' + ', '.join(unresolved(state)))


def context(root):
    state = d.status(root)
    memory = state.get('context', {'revision': 0, 'items': {}, 'receipts': {}})
    index = []
    for item in memory['items'].values():
        fresh = True
        for ref in item['sources']:
            try:
                source(root, ref)
            except (d.DeliveryError, OSError):
                fresh = False
        index.append({'id': item['id'], 'revision': item['revision'], 'summary': item['summary'], 'kind': item['kind'], 'fresh': fresh, 'sources': item['sources']})
    return {'run_id': state['run_id'], 'contract_hash': state['contract_hash'], 'revision': memory['revision'], 'fingerprint': d.digest(d.snapshot(root)), 'goal': state['request'], 'criteria': state['contract']['criteria'], 'scope': state['contract']['scope'], 'phase': state['phase'], 'status': state['status'], 'deadline': state['deadline'], 'repairs': state['repairs'], 'index': index, 'blockers': [{'id': b['id'], 'family': b['family'], 'target': b['target'], 'status': b['status'], 'attempts': len(b['attempts'])} for b in state.get('blockers', {}).values()], 'alternative': state.get('alternative'), 'push_attempted': bool(state.get('push_attempted'))}


def import_context(root, proposal):
    with d.locked(root) as directory:
        state = d.load(directory)
        d.expire(state)
        d.save(directory, state)
        d.active(state)
        d.require(proposal.get('run_id') == state['run_id'] and proposal.get('contract_hash') == state['contract_hash'], 'Context belongs to another task/contract')
        memory = state.setdefault('context', {'revision': 0, 'items': {}, 'receipts': {}})
        proposal_id = text(proposal.get('proposal_id'), 100)
        payload_hash = d.digest(proposal)
        receipt = memory['receipts'].get(proposal_id)
        if receipt:
            d.require(receipt['hash'] == payload_hash, 'Conflicting proposal replay')
            return receipt
        d.require(len(memory['receipts']) < 500, 'Task context proposal ceiling reached; preserve state rather than reset')
        d.require(proposal.get('expected_revision') == memory['revision'], 'Stale context revision; reread and reconcile')
        d.require(proposal.get('expected_fingerprint') == d.digest(d.snapshot(root)), 'Stale code fingerprint')
        steward = text(proposal.get('steward'), 200)
        items = proposal.get('items')
        d.require(isinstance(items, list) and 0 < len(items) <= 20, 'Import 1–20 focused items')
        updated = copy.deepcopy(memory['items'])
        seen = set()
        for item in items:
            key = text(item.get('id'), 64)
            d.require(re.fullmatch(r'[a-zA-Z0-9_-]+', key) and key not in seen, 'Invalid/duplicate memory ID')
            seen.add(key)
            d.require(item.get('kind') in ('fact', 'hypothesis', 'decision'), 'Unknown memory kind')
            updated[key] = {'id': key, 'revision': memory['revision'] + 1, 'summary': text(item.get('summary'), 200), 'kind': item['kind'], 'text': text(item.get('text')), 'sources': sources(root, item.get('sources')), 'recorded_at': time.time(), 'steward': steward}
        d.require(len(updated) <= 100, 'Keep task memory bounded: update existing records, do not accumulate')
        memory['items'] = updated
        memory['revision'] += 1
        receipt = {'hash': payload_hash, 'revision': memory['revision'], 'proposal_id': proposal_id}
        memory['receipts'][proposal_id] = receipt
        d.event(state, 'context-import', {'receipt': receipt, 'steward': steward, 'items': [updated[key] for key in seen]})
        if state['status'] == 'ready':
            state['status'] = 'active'
            state['review'] = None
        d.save(directory, state)
        return receipt


def human_resolve(root, report):
    """Host approval is required; this record itself is not authorization proof."""
    with d.locked(root) as directory:
        state = d.load(directory)
        d.active(state)
        d.require(report.get('run_id') == state['run_id'], 'Wrong task identity')
        record = state.get('blockers', {}).get(report.get('id'))
        d.require(record and record['status'] == 'human-required', 'No matching human-only blocker')
        authorization = text(report.get('authorization'))
        evidence = sources(root, report.get('evidence'))
        record['status'] = 'resolved'
        record['resolution'] = {'authorization': authorization, 'evidence': evidence, 'at': time.time()}
        state['checks'] = {}
        state['review'] = None
        state['status'] = 'active'
        state['phase'] = 'implement'
        d.event(state, 'human-resolution', copy.deepcopy(record))
        d.save(directory, state)
        return record


def item(root, key):
    state = d.status(root)
    value = state.get('context', {}).get('items', {}).get(key)
    d.require(value is not None, 'Unknown context item')
    return value


def blocker(root, operation):
    with d.locked(root) as directory:
        state = d.load(directory)
        d.expire(state)
        d.save(directory, state)
        d.active(state)
        d.require(operation.get('run_id') == state['run_id'], 'Blocker operation belongs to another task')
        blocks = state.setdefault('blockers', {})
        op = operation.get('op')
        if op == 'open':
            family = operation.get('family')
            d.require(family in FAMILIES, 'Unknown blocker family')
            target = ' '.join(text(operation.get('target'), 300).split()).casefold()
            key = d.digest({'run_id': state['run_id'], 'family': family, 'target': target})
            found = next((b for b in blocks.values() if b['key'] == key), None)
            evidence = sources(root, operation.get('evidence'))
            if found:
                found['evidence'].extend(ref for ref in evidence if ref not in found['evidence'])
                if found['status'] not in ('attempting', 'reconciliation-required', 'alternative-selected', 'human-required'):
                    found['status'] = 'human-required' if family in HUMAN else ('escalated' if len(found['attempts']) >= found['limit'] else 'open')
                record = found
            else:
                d.require(len(blocks) < 50, 'Task blocker ceiling reached')
                criteria = operation.get('criteria')
                d.require(isinstance(criteria, list) and criteria and set(criteria) <= {c['id'] for c in state['contract']['criteria']}, 'Blocker must name existing criteria')
                identity = 'B-' + uuid.uuid4().hex[:12]
                record = {'id': identity, 'key': key, 'family': family, 'target': target, 'criteria': criteria, 'status': 'human-required' if family in HUMAN else 'open', 'limit': min(3, state['contract'].get('max_repairs', 3)), 'attempts': [], 'evidence': evidence}
                if family not in HUMAN and (record['limit'] == 0 or state['repairs'] >= d.repair_limit(state)):
                    record['status'] = 'escalated'
                blocks[identity] = record
        else:
            record = blocks.get(operation.get('id'))
            d.require(record is not None, 'Unknown blocker')
            if op == 'attempt':
                d.require(record['family'] not in HUMAN, 'Human-only blockers cannot be retried by agents')
                d.require(record['status'] == 'open', 'Preserve human-only, pending and reconciliation states; no corrective attempt eligible')
                if state['repairs'] >= d.repair_limit(state):
                    record['status'] = 'escalated'
                    d.event(state, 'blocker-escalated', copy.deepcopy(record))
                    d.save(directory, state)
                    raise d.DeliveryError('Global repair allowance exhausted; consultation required, not a corrective attempt')
                d.require(record['status'] == 'open' and len(record['attempts']) < record['limit'], 'Attempt ceiling reached; consult Advisor/Architect/PM, not another retry')
                d.require(not any(a['outcome'] == 'pending' for a in record['attempts']), 'Reconcile pending attempt before starting another')
                action = ' '.join(text(operation.get('action'), 500).split()).casefold()
                hypothesis = text(operation.get('hypothesis'))
                evidence = sources(root, operation.get('evidence'))
                identity = d.digest({'action': action, 'hypothesis': hypothesis, 'evidence': evidence})
                d.require(not any(a['key'] == identity for a in record['attempts']), 'Unchanged failed attempt refused')
                attempt = {'id': uuid.uuid4().hex, 'key': identity, 'ordinal': len(record['attempts']) + 1, 'action': action, 'hypothesis': hypothesis, 'evidence': evidence, 'fingerprint': d.digest(d.snapshot(root)), 'at': time.time(), 'outcome': 'pending'}
                record['attempts'].append(attempt)
                record['status'] = 'attempting'
            elif op == 'result':
                d.require(record['attempts'] and record['status'] == 'attempting', 'No pending attempt')
                attempt = record['attempts'][-1]
                d.require(operation.get('attempt_id') == attempt['id'] and attempt['outcome'] == 'pending', 'Result does not match pending attempt')
                d.require(operation.get('outcome') in ('failed', 'candidate-fix', 'ambiguous'), 'Unknown attempt result')
                attempt['result_refs'] = sources(root, operation.get('evidence'))
                attempt['outcome'] = operation['outcome']
                record['status'] = 'reconciliation-required' if operation['outcome'] == 'ambiguous' else ('escalated' if len(record['attempts']) >= record['limit'] else 'open')
            elif op == 'reconcile':
                d.require(record['status'] == 'reconciliation-required', 'No ambiguous attempt awaiting reconciliation')
                attempt = record['attempts'][-1]
                d.require(operation.get('attempt_id') == attempt['id'], 'Reconcile the exact ambiguous attempt')
                refs = sources(root, operation.get('evidence'))
                d.require(refs != attempt.get('result_refs'), 'Reconciliation needs new observed-state evidence')
                d.require(operation.get('outcome') in ('failed', 'candidate-fix'), 'Establish actual outcome before continuing')
                attempt['reconciliation'] = {'outcome': operation['outcome'], 'evidence': refs, 'at': time.time()}
                record['status'] = 'escalated' if len(record['attempts']) >= record['limit'] or state['repairs'] >= d.repair_limit(state) else 'open'
            elif op == 'decision':
                d.require(record['status'] == 'escalated', 'Decision follows exhausted technical attempts')
                d.require(operation.get('owner') == 'pm' and {'advisor', 'architect'} <= set(operation.get('consulted', [])), 'PM decision requires Advisor and Architect consultation')
                consultation = sources(root, operation.get('evidence'))
                plan = text(operation.get('plan'))
                choice = operation.get('choice')
                d.require(choice in ('alternative', 'human-required', 'prioritize-independent'), 'Unknown escalation choice')
                if choice == 'alternative':
                    d.require(not state.get('alternative'), 'Only one bounded alternative per task, never repeated reset cycles')
                    d.require(state['repairs'] < d.repair_limit(state), 'No remaining repair budget for another route')
                    state['alternative'] = {'blocker_id': record['id'], 'plan': plan, 'evidence': consultation, 'at': time.time(), 'deadline': state['deadline']}
                    record['status'] = 'alternative-selected'
                elif choice == 'human-required':
                    record['status'] = 'human-required'
                record['decision'] = {'owner': 'pm', 'consulted': operation['consulted'], 'choice': choice, 'plan': plan, 'evidence': consultation}
            elif op == 'resolve':
                d.require(record['family'] not in HUMAN and record['status'] != 'human-required', 'Human-only blocker requires explicit user reconciliation, not agent resolution')
                d.require(record['status'] not in ('attempting', 'reconciliation-required'), 'Record/reconcile the pending attempt outcome first')
                refs = sources(root, operation.get('evidence'))
                fingerprint = d.digest(d.snapshot(root))
                for criterion in state['contract']['criteria']:
                    if criterion['id'] in record['criteria']:
                        for check_id in criterion['checks']:
                            result = state['checks'].get(check_id, {})
                            d.require(result.get('status') == 'passed' and result.get('fingerprint') == fingerprint, 'Resolution requires current passing checks for affected criteria')
                record['status'] = 'resolved'
                record['resolution'] = {'evidence': refs, 'fingerprint': fingerprint, 'at': time.time()}
            else:
                raise d.DeliveryError('Unknown blocker operation')
        # Updating blocker knowledge invalidates readiness; no hidden release bypass.
        if state['status'] == 'ready':
            state['status'] = 'active'
        state['review'] = None
        d.event(state, 'blocker-' + op, copy.deepcopy(record))
        d.save(directory, state)
        return record
