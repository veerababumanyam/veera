"""Explicit isolated ownership setup for local controller tests."""
from pathlib import Path
import uuid
from unittest.mock import patch
import ownership
import delivery as d


def bind(test, root):
    registry = Path(test.enterContext(__import__('tempfile').TemporaryDirectory())) / 'sessions'
    test.enterContext(patch.object(ownership, 'REGISTRY', registry))
    session_id = 'fixture-' + uuid.uuid4().hex
    directory = d.storage(root)
    d.atomic(directory / 'workspace.json', {'id': session_id, 'session_id': session_id})
    capability = ownership.enroll(session_id, root, session_id)
    return session_id, capability


def cli(test, *args):
    import contextlib
    import io
    import sys
    output, errors = io.StringIO(), io.StringIO()
    code = 0
    with patch.object(sys, 'argv', ['delivery', *args, '--session-id', test.session_id, '--capability-file', test.capability]), contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
        try:
            d.main()
        except SystemExit as exit:
            code = exit.code
    return __import__('subprocess').CompletedProcess(args, code, output.getvalue(), errors.getvalue())
