#!/usr/bin/env python
"""
Improved decompile_abc.py
- Accepts: base64 ABC as positional arg
- Optional flag: --zip  (emit a ZIP of per-class .as files to stdout as binary)
- Produces: AS3 skeleton with per-class method stubs and disassembly comments
"""
from __future__ import annotations
import sys
import base64
import argparse
import io
import zipfile
from pathlib import Path
# Ensure repo root is on sys.path so package imports work
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import py_swf.avm2 as avm2


def build_class_files(abc: avm2.ABCFile):
    """Wrapper: delegate class reconstruction to dedicated module.
    Falls back to a simple listing if reconstruction fails.
    """
    try:
        from py_swf.tools.class_reconstruct import reconstruct_classes
        return reconstruct_classes(abc)
    except Exception:
        # graceful fallback: produce simple stubs
        pool = abc.constant_pool
        files = {}
        for inst_idx, inst in enumerate(getattr(abc, 'instances', [])):
            try:
                name = avm2.resolve_multiname(pool, inst.name)
            except Exception:
                name = f'Class_{inst_idx}'
            safe = name.split('::')[-1] if '::' in name else name or f'Class_{inst_idx}'
            lines = [f'// Decompiled class: {name}', 'package {', f'    public class {safe} {{', '    }', '}']
            files[f'{safe}.as'] = '\n'.join(lines)
        files['module_index.txt'] = '// fallback index'
        return files


def main():
    parser = argparse.ArgumentParser(description='Decompile ABC payload to AS3 skeleton or ZIP of .as files')
    parser.add_argument('b64', help='base64-encoded ABC payload')
    parser.add_argument('--zip', action='store_true', help='Emit a ZIP with per-class .as files to stdout (binary)')
    args = parser.parse_args()

    try:
        abc_bytes = base64.b64decode(args.b64)
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

    # Quick human-readable header
    header_lines = []
    header_lines.append(f'// ABC version: {abc.major_version}.{abc.minor_version}')
    header_lines.append('// --- Constant pool strings (sample, up to 80) ---')
    for i, s in enumerate(pool.strings[:80]):
        if s and len(s) > 0:
            header_lines.append(f'// [{i}] "{s}"')

    # Build class files
    files = build_class_files(abc)

    if args.zip:
        # Emit ZIP to stdout as binary
        bio = io.BytesIO()
        with zipfile.ZipFile(bio, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            # Add a header file
            zf.writestr('README.txt', '\n'.join(header_lines))
            for name, content in files.items():
                zf.writestr(name, content)
        bio.seek(0)
        sys.stdout.buffer.write(bio.read())
        return

    # Otherwise, print a single AS3 skeleton with all class contents concatenated
    out = []
    out.extend(header_lines)
    out.append('\n// --- Generated AS3 class files ---\n')
    for name, content in files.items():
        out.append(f'// File: {name}\n')
        out.append(content)
        out.append('\n')

    print('\n'.join(out))


if __name__ == '__main__':
    main()
