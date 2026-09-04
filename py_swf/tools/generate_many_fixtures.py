"""Generate many synthetic ABC fixtures for corpus testing."""
import sys
from pathlib import Path
import base64
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
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


def main(n=50):
    n = int(n)
    for i in range(1, n+1):
        name = f'com.example.fixture{str(i).zfill(3)}'
        data = build_basic_abc(name)
        p = OUT_DIR / f'fixture_{i:03d}.abc'
        p.write_bytes(data)
        (OUT_DIR / f'fixture_{i:03d}.abc.b64').write_text(base64.b64encode(data).decode('ascii'))
    print(f'Wrote {n} fixtures to {OUT_DIR}')

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 50)
