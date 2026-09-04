import base64
import subprocess
import sys
import io
import zipfile
from pathlib import Path

import pytest

# Use local repo python to ensure module imports resolve
PY = sys.executable

from py_swf import avm2


def build_simple_abc():
    abc = avm2.ABCFile()
    # minimal constant pool to avoid errors
    abc.constant_pool.strings = [""]
    # add a simple instance/class skeleton
    inst = avm2.InstanceInfo()
    # use helper to add multiname into pool
    name_idx = avm2.search_or_add_multiname(abc.constant_pool, "com.example::Simple")
    inst.name = name_idx
    abc.instances = [inst]
    # Add matching ClassInfo for each instance
    cls = avm2.ClassInfo()
    abc.classes = [cls]
    # serialize
    data = abc.serialize()
    return data


def run_decompile(b64, zip_mode=False):
    args = [PY, str(Path('py_swf') / 'tools' / 'decompile_abc.py'), b64]
    if zip_mode:
        args.append('--zip')
        p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return p.returncode, p.stdout, p.stderr
    else:
        p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return p.returncode, p.stdout, p.stderr


def test_decompile_text_and_zip():
    abc_bytes = build_simple_abc()
    b64 = base64.b64encode(abc_bytes).decode('ascii')

    rc, out, err = run_decompile(b64, zip_mode=False)
    assert rc == 0, f"decompile failed: {err}"
    assert "ABC version" in out or "Generated AS3" in out or "File:" in out

    rc, outb, err = run_decompile(b64, zip_mode=True)
    assert rc == 0, f"zip decompile failed: {err}"
    # validate zip buffer
    bio = io.BytesIO(outb)
    with zipfile.ZipFile(bio, 'r') as zf:
        names = zf.namelist()
        assert 'README.txt' in names
        # there should be at least one .as file
        assert any(n.endswith('.as') for n in names)


def test_decompile_fixture_files():
    fixtures_dir = Path('tests') / 'fixtures'
    files = list(fixtures_dir.glob('*.abc'))
    assert files, 'No fixture abc files found'
    for fpath in files:
        b = fpath.read_bytes()
        b64 = base64.b64encode(b).decode('ascii')
        rc, out, err = run_decompile(b64, zip_mode=False)
        assert rc == 0, f"decompile failed on {fpath}: {err}"
        rc, outb, err = run_decompile(b64, zip_mode=True)
        assert rc == 0, f"zip decompile failed on {fpath}: {err}"
        # try open zip
        bio = io.BytesIO(outb)
        with zipfile.ZipFile(bio, 'r') as zf:
            names = zf.namelist()
            assert 'README.txt' in names
