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
    """Return a dict mapping filename -> content for each inferred class."""
    pool = abc.constant_pool
    files = {}

    # Helper to get readable name for an instance/class
    def inst_name(inst_idx, inst: avm2.InstanceInfo):
        try:
            return avm2.resolve_multiname(pool, inst.name)
        except Exception:
            return f"Instance_{inst_idx}"

    # Map method index -> method name
    method_names = {}
    for mi_idx, m in enumerate(abc.methods):
        try:
            method_names[mi_idx] = pool.strings[m.name] if m.name < len(pool.strings) else f"method_{mi_idx}"
        except Exception:
            method_names[mi_idx] = f"method_{mi_idx}"

    # Map method index -> method body (if present)
    method_bodies = {}
    for mb in abc.method_bodies:
        method_bodies[mb.method] = mb

    # For each instance (class), gather traits that are methods
    for inst_idx, inst in enumerate(abc.instances):
        cls_name = inst_name(inst_idx, inst)
        # Heuristic: take last segment after '::' as simple class name
        if '::' in cls_name:
            simple_name = cls_name.split('::')[-1]
        else:
            simple_name = cls_name or f'Class_{inst_idx}'
        if not simple_name:
            simple_name = f'Class_{inst_idx}'

        lines = []
        lines.append(f'// Decompiled class: {cls_name}')
        lines.append('package {')
        lines.append(f'    public class {simple_name} {{')
        lines.append('        public function ' + simple_name + '() {')
        lines.append('            // constructor (from iinit if available)')
        lines.append('        }')
        lines.append('')

        # Iterate instance traits to find method traits
        for t in inst.traits:
            kind = t.kind_flags & 0x0F
            # kinds 1..3 are methods/getter/setter per parser
            if kind in (1, 2, 3):
                method_idx = getattr(t, 'method', None)
                if method_idx is None:
                    continue
                name = method_names.get(method_idx, f'method_{method_idx}')
                func_name = name or f'method_{method_idx}'
                lines.append(f'        // Trait kind={kind} method idx={method_idx}')
                lines.append(f'        public function {func_name}(...args):* {{')
                # If method body exists, embed disassembly as comment and basic blocks
                mb = method_bodies.get(method_idx)
                if mb:
                    try:
                        disasm = avm2.disassemble_instructions(pool, mb.code)
                    except Exception as e:
                        disasm = f'// Disassembly failed: {e}'
                    # Include disassembly as commented block
                    lines.append('            /* disassembly:')
                    for dl in disasm.splitlines():
                        lines.append('            ' + dl)
                    lines.append('            */')
                else:
                    lines.append('            // no method body available in this ABC')
                lines.append('            // TODO: reconstruct high-level body')
                lines.append('        }')
                lines.append('')

        lines.append('    }')
        lines.append('}')

        filename = f'{simple_name}.as'
        files[filename] = '\n'.join(lines)

    # Additionally, include a top-level module that lists all classes
    mod_lines = []
    mod_lines.append('// Decompiled module index')
    mod_lines.append('package {')
    mod_lines.append('    // Classes:')
    for fn in sorted(files.keys()):
        mod_lines.append(f'    // - {fn}')
    mod_lines.append('}')
    files['module_index.txt'] = '\n'.join(mod_lines)

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
