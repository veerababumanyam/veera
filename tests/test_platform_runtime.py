import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from platform_runtime import file_lock, launch
from delivery import kill_group


class PlatformTests(unittest.TestCase):
    def test_lock_exclusion_and_release_across_processes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'lock'
            program = ('import sys; sys.path.insert(0, sys.argv[1]); '
                       'from platform_runtime import file_lock; '
                       'lock=file_lock(sys.argv[2], blocking=False); lock.__enter__(); lock.__exit__(None,None,None)')
            argv = [sys.executable, '-c', program, str(ROOT / 'scripts'), str(path)]
            with file_lock(path):
                result = subprocess.run(argv, capture_output=True, timeout=5)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'BlockingIOError', result.stderr)
            self.assertEqual(subprocess.run(argv, capture_output=True, timeout=5).returncode, 0)

    def test_codex_manifest_selects_adapter(self):
        manifest = json.loads((ROOT / '.codex-plugin/plugin.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['skills'], './adapters/codex/skills')
        hooks = json.loads((ROOT / manifest['hooks']).read_text(encoding='utf-8'))
        for groups in hooks['hooks'].values():
            self.assertIn('codex_hook.py', groups[0]['hooks'][0]['commandWindows'])

    @unittest.skipUnless(os.name == 'nt', 'Windows hook command')
    def test_windows_hook_bootstrap_with_fixture_identity(self):
        # Isolated fixture only; never used as a live host session/bootstrap.
        hooks = json.loads((ROOT / 'adapters/codex/hooks.json').read_text(encoding='utf-8'))
        command = hooks['hooks']['UserPromptSubmit'][0]['hooks'][0]['commandWindows']
        with tempfile.TemporaryDirectory() as directory:
            env = dict(os.environ, PLUGIN_ROOT=str(ROOT), CLAUDE_PLUGIN_ROOT=str(ROOT),
                       PLUGIN_DATA=directory, CLAUDE_PLUGIN_DATA=directory)
            linked_start = r'[$veera:start](C:\Users\VeeraDesktop\.codex\plugins\cache\veera-plugins\veera\0.2.5\adapters\codex\skills\start\SKILL.md)'
            for trigger in ('$veera:start', '$veera-start', '$veera:fix Repair fixture', '$veera-build Create fixture', linked_start):
                payload = {'hook_event_name':'UserPromptSubmit','session_id':'test-fixture-only','prompt':trigger,'cwd':directory}
                result = subprocess.run(['powershell.exe','-NoProfile','-Command', command], input=json.dumps(payload), env=env, capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                context = json.loads(result.stdout)['hookSpecificOutput']['additionalContext']
                self.assertIn('"host": "codex"', context)
                self.assertIn('package_root', context)
                self.assertEqual(list(Path(directory).iterdir()), [])

    @unittest.skipUnless(os.name == 'nt', 'Windows job teardown')
    def test_timeout_terminates_descendant(self):
        import ctypes
        from ctypes import wintypes as w
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
        kernel.OpenProcess.restype = w.HANDLE
        kernel.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
        kernel.WaitForSingleObject.restype = w.DWORD
        kernel.CloseHandle.argtypes = [w.HANDLE]
        with tempfile.TemporaryDirectory() as directory:
            program = "import subprocess,sys,time; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); print(p.pid,flush=True); time.sleep(30)"
            process = launch([sys.executable, '-c', program], directory)
            handle = None
            try:
                pid = int(process.stdout.readline())
                handle = kernel.OpenProcess(0x100000, False, pid)
                self.assertTrue(handle)
                kill_group(process)
                self.assertEqual(kernel.WaitForSingleObject(handle, 3000), 0)
            finally:
                kill_group(process)
                process.stdout.close()
                if handle:
                    kernel.CloseHandle(handle)
