"""Repeatable local runtime benchmark; isolated fixture, no model/network calls."""
import argparse
import cProfile
import io
import json
import os
from pathlib import Path
import pstats
import statistics
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def measure(call, count):
    for _ in range(3):
        call()
    samples = []
    for _ in range(count):
        start = time.perf_counter()
        call()
        samples.append((time.perf_counter() - start) * 1000)
    return {'median_ms': round(statistics.median(samples), 3),
            'p95_ms': round(sorted(samples)[int(.95 * (len(samples) - 1))], 3), 'samples': count}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--package', type=Path, default=ROOT, help='Compare another installed local package with the same fixture')
    args = parser.parse_args()
    package = args.package.resolve()
    sys.path.insert(0, str(package / 'scripts'))
    import delivery
    import ownership
    import codex_hook
    import model_router
    with tempfile.TemporaryDirectory(prefix='veera-perf-') as temp:
        root = Path(temp) / 'task'
        root.mkdir()
        subprocess.run(['git', 'init', '-q', str(root)], check=True)
        (root / 'app.py').write_text('value = 1\n')
        contract = {'scope': ['app.py'], 'non_goals': [],
                    'criteria': [{'id': 'C1', 'text': 'Fixture', 'checks': ['unit']}],
                    'checks': [{'id': 'unit', 'kind': 'test', 'argv': [sys.executable, '-m', 'unittest'], 'count_pattern': r'Ran (\d+) test'}]}
        delivery.init(root, 'fix', 'Performance fixture', contract, 10)
        with delivery.locked(root) as directory:
            state = delivery.load(directory)
            for i in range(50):
                delivery.event(state, 'fixture', {'step': i, 'detail': 'A representative task event'})
            delivery.save(directory, state)
            delivery.atomic(directory / 'workspace.json', {'id': 'fixture-workspace', 'session_id': 'perf-fixture'})
        env = {'VEERA_HOST': 'codex', 'CLAUDE_PLUGIN_DATA': str(Path(temp) / 'plugin-data')}
        with patch.dict(os.environ, env), patch.object(ownership, 'REGISTRY', None):
            ownership.enroll('perf-fixture', root, 'fixture-workspace')
            payload = {'hook_event_name': 'PreToolUse', 'session_id': 'perf-fixture', 'cwd': str(root),
                       'tool_name': 'exec_command', 'tool_input': {'cmd': 'python -m unittest'}}
            child = lambda: subprocess.run([sys.executable, str(package / 'scripts/codex_hook.py')],
                         input=json.dumps(payload), text=True, capture_output=True, check=True)
            report = {'package': str(package), 'python': sys.version.split()[0], 'fixture_events': 51,
                      'status': measure(lambda: delivery.status(root), 100),
                      'owned_hook': measure(lambda: codex_hook.handle(payload), 100),
                      'hook_process': measure(child, 25),
                      'native_route': measure(lambda: model_router.execute('Summarize README', root, 'codex'), 100)}
            profile = cProfile.Profile()
            profile.runcall(lambda: [codex_hook.handle(payload) for _ in range(30)])
            stream = io.StringIO()
            pstats.Stats(profile, stream=stream).sort_stats('cumulative').print_stats(12)
            report['owned_hook_profile'] = stream.getvalue()
        args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps({key: value for key, value in report.items() if key != 'owned_hook_profile'}, indent=2))


if __name__ == '__main__':
    main()
