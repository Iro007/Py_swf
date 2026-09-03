#!/usr/bin/env python
import sys
import base64
from pathlib import Path
# Ensure repo root is on sys.path so package imports work
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import py_swf.avm2 as avm2
ByteReader = avm2.ByteReader
parse_constant_pool = avm2.parse_constant_pool

# Script: decompile_abc.py
# Input: base64 ABC payload as first argument
# Output: AS3 skeleton + constant pool strings + disassembly per method body

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

    abc = avm2.ABCFile()
    try:
        abc.parse(abc_bytes)
    except Exception as e:
        print(f'ERROR: failed to parse ABC: {e}', file=sys.stderr)
        sys.exit(3)

    pool = abc.constant_pool

    out = []
    out.append(f'// ABC version: {abc.major_version}.{abc.minor_version}')
    out.append('// --- Constant pool strings (sample, up to 80) ---')
    for i, s in enumerate(pool.strings[:80]):
        if s and len(s) > 0:
            out.append(f'// [{i}] "{s}"')

    out.append('\npackage {')
    out.append('    import flash.display.Sprite;')
    out.append('    import flash.events.Event;')
    out.append('')
    out.append('    public class DecompiledModule extends Sprite {')
    out.append('        public function DecompiledModule() {')
    out.append('            super();')
    out.append('            trace("DecompiledModule initialized");')
    out.append('        }')
    out.append('')

    # Disassemble method bodies
    out.append('        // --- Decompiled method bodies (disassembly) ---')
    for idx, mb in enumerate(abc.method_bodies):
        try:
            disasm = avm2.disassemble_instructions(pool, mb.code)
        except Exception as e:
            disasm = f'// Disassembly failed: {e}'
        out.append(f'\n        // MethodBody #{idx} (method index {mb.method}) - max_stack={mb.max_stack} local_count={mb.local_count}')
        for line in disasm.splitlines():
            out.append('        // ' + line)

    out.append('\n        // --- End of decompiled module ---')
    out.append('    }')
    out.append('}')

    print('\n'.join(out))

if __name__ == '__main__':
    main()
