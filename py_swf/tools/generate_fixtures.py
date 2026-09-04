"""Generate synthetic ABC fixtures and SWF wrappers for tests/fixtures.
Run this script from repo root to produce tests/fixtures/abc1.abc, abc2.abc and their base64 variants.
"""
import os
from pathlib import Path
import base64
import sys
from pathlib import Path as _P
sys.path.insert(0, str(_P(__file__).resolve().parents[2]))
import py_swf.avm2 as avm2

OUT_DIR = Path('tests') / 'fixtures'
OUT_DIR.mkdir(parents=True, exist_ok=True)


def build_basic_abc(name):
    abc = avm2.ABCFile()
    abc.constant_pool.strings = [""]
    inst = avm2.InstanceInfo()
    idx = avm2.search_or_add_multiname(abc.constant_pool, name)
    inst.name = idx
    abc.instances = [inst]
    abc.classes = [avm2.ClassInfo()]
    return abc.serialize()


if __name__ == '__main__':
    a1 = build_basic_abc('com.example.FixtureOne')
    a2 = build_basic_abc('com.example.FixtureTwo')

    (OUT_DIR / 'fixture_one.abc').write_bytes(a1)
    (OUT_DIR / 'fixture_two.abc').write_bytes(a2)

    (OUT_DIR / 'fixture_one.abc.b64').write_text(base64.b64encode(a1).decode('ascii'))
    (OUT_DIR / 'fixture_two.abc.b64').write_text(base64.b64encode(a2).decode('ascii'))

    print(f'Wrote fixtures to {OUT_DIR}')
