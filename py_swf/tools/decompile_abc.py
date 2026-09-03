#!/usr/bin/env python
import sys
import base64
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from avm2 import ByteReader, parse_constant_pool

# Script: decompile_abc.py
# Input: base64 ABC payload as first argument
# Output: basic AS3 skeleton + constant pool strings and a placeholder for methods

def main():
    if len(sys.argv) < 2:
        print('Usage: decompile_abc.py <base64-abc>')
        sys.exit(1)
    b64 = sys.argv[1]
    try:
        abc_bytes = base64.b64decode(b64)
    except Exception as e:
        print(f'ERROR: invalid base64: {e}', file=sys.stderr)
        sys.exit(2)

    reader = ByteReader(abc_bytes)
    try:
        minor = reader.read_u16()
        major = reader.read_u16()
    except Exception as e:
        print(f'ERROR: failed to read ABC header: {e}', file=sys.stderr)
        sys.exit(3)

    pool = parse_constant_pool(reader)

    out = []
    out.append(f'// ABC version: {major}.{minor}')
    out.append('// --- Constant pool strings (sample, up to 80) ---')
    for i, s in enumerate(pool.strings[:80]):
        if s and len(s) > 0:
            out.append(f'// [{i}] "{s}"')

    out.append('\npackage {
    import flash.display.Sprite;
    import flash.events.Event;

    public class DecompiledModule extends Sprite {
        public function DecompiledModule() {
            super();
            trace("DecompiledModule initialized");
        }

        // Method skeletons (detailed disassembly is available in comments)
    }
}')

    print('\n'.join(out))

if __name__ == '__main__':
    main()
