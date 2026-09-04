import subprocess
import sys
import os

PY = sys.executable
SCRIPT = os.path.join(os.path.dirname(__file__), '..', 'py_swf', 'tools', 'decompile_abc.py')


def test_invalid_base64_exits_nonzero():
    p = subprocess.run([PY, SCRIPT, '!!!notbase64!!!'], capture_output=True)
    # Our script exits with code 2 on invalid base64
    assert p.returncode == 2
    assert b'ERROR: invalid base64' in p.stderr
