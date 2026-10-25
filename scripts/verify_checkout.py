"""Verify a source checkout using only the project's existing test tools."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def run(argv):
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True,
                            encoding='utf-8', errors='replace',
                            env={**os.environ, 'PYTHONUTF8': '1'}, timeout=1800)
    return argv, result


def clean():
    result = subprocess.run(['git', 'status', '--porcelain'], cwd=ROOT,
                            capture_output=True, text=True, check=True)
    if result.stdout:
        raise RuntimeError('Checkout is not clean:\n' + result.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-clean', action='store_true')
    parser.add_argument('--jobs', type=int, choices=range(1, 9), default=1)
    parser.add_argument('--browser', action='store_true', help='Require installed Chrome or Edge')
    args = parser.parse_args()
    if args.require_clean:
        clean()
    # Compile in memory: no build dependencies or generated source files.
    for folder in ('scripts', 'tests'):
        for path in sorted((ROOT / folder).glob('*.py')):
            compile(path.read_bytes(), str(path), 'exec')
    commands = [['node', '--check', str(p)] for p in sorted((ROOT / 'web').glob('*.js'))]
    commands += [['node', 'tests/test_web.js'], ['node', 'tests/test_dashboard_ui.cjs']]
    commands += [[sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', p.name, '-v']
                 for p in sorted((ROOT / 'tests').glob('test_*.py'))]
    if args.browser:
        commands.append([sys.executable, 'tests/browser_smoke.py'])
    failed = False
    # Every module gets its own process, preserving environment and fixture isolation.
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for argv, result in pool.map(run, commands):
            print(('PASS ' if result.returncode == 0 else 'FAIL ') + ' '.join(argv), flush=True)
            print(result.stdout + result.stderr, flush=True)
            failed |= result.returncode != 0
    if args.require_clean:
        clean()
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())
