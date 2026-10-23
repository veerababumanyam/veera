"""Portable file locks and bounded check processes (Python 3.12+ on Windows)."""
import contextlib
import os
from pathlib import Path
import subprocess
import sys
import time


def make_state_directory(path, *, parents=False, exist_ok=False):
    """Keep POSIX state private; inherit host-managed Windows access on creation.

    Python 3.13+ turns mode 0700 into a protected Windows DACL, removing
    inherited host/sandbox entries. The default Windows mkdir instead uses
    the parent's ACL. Existing permissions and actual denials are untouched.
    """
    if os.name == 'nt':
        path.mkdir(parents=parents, exist_ok=exist_ok)
    else:
        path.mkdir(mode=0o700, parents=parents, exist_ok=exist_ok)


@contextlib.contextmanager
def file_lock(path, blocking=True):
    with open(path, 'a+b') as stream:
        if os.name == 'nt':
            import msvcrt
            # Lock the same byte in every process, even for an empty file.
            while True:
                stream.seek(0)
                try:
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError as error:
                    if error.errno not in (13, 36):
                        raise
                    if not blocking:
                        raise BlockingIOError('Veera lock is already held') from error
                    time.sleep(.05)
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
            yield


def launch(argv, cwd):
    if os.name == 'nt':
        argv = [sys.executable, str(Path(__file__).with_name('windows_check.py')), *argv]
    return subprocess.Popen(argv, cwd=cwd, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, start_new_session=True, bufsize=0)
