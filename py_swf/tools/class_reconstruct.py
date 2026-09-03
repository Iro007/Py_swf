"""Class reconstruction helpers for ABC decompilation.
Provides reconstruct_classes(abc) -> dict filename->content
"""
from typing import Dict
from pathlib import PurePosixPath
import py_swf.avm2 as avm2


def sanitize_filename(s: str) -> str:
    # Replace characters invalid for filenames with underscore
    if not s:
        return 'unnamed'
    return ''.join(ch if (ch.isalnum() or ch in ('_', '-')) else '_' for ch in s)


def reconstruct_classes(abc: avm2.ABCFile, name_maps=None) -> Dict[str, str]:
    pool = abc.constant_pool
    files = {}

    # Build name maps if not provided
    if name_maps is None:
        try:
            from py_swf.tools.infer_names import infer_names
            name_maps = infer_names(abc)
        except Exception:
            name_maps = {'multiname': {}, 'string': {}}

    # Map method index -> name
    method_names = {}
    for mi, m in enumerate(abc.methods):
        try:
            if m.name in name_maps.get('string', {}):
                method_names[mi] = name_maps['string'][m.name]
            else:
                method_names[mi] = pool.strings[m.name] if m.name < len(pool.strings) else f'method_{mi}'
        except Exception:
            method_names[mi] = f'method_{mi}'

    # Map method index -> body
    method_bodies = {mb.method: mb for mb in abc.method_bodies}

    def resolve_inst_name(idx, inst):
        try:
            resolved = avm2.resolve_multiname(pool, inst.name)
        except Exception:
            resolved = None
        if inst.name in name_maps.get('multiname', {}):
            return name_maps['multiname'][inst.name]
        if resolved:
            return resolved
        return f'Instance_{idx}'

    for idx, inst in enumerate(abc.instances):
        full_name = resolve_inst_name(idx, inst)
        # namespace::ClassName or just ClassName
        if '::' in full_name:
            ns, cls = full_name.split('::', 1)
        else:
            ns, cls = '', full_name
        simple_cls = cls or f'Class_{idx}'
        pkg_path = ns.replace('.', '/').replace(':', '_') if ns else ''
        safe_cls = sanitize_filename(simple_cls)
        if pkg_path:
            filename = f'{pkg_path}/{safe_cls}.as'
        else:
            filename = f'{safe_cls}.as'

        lines = []
        lines.append(f'// Decompiled class: {full_name}')
        if ns:
            lines.append(f'package {ns} {{')
            indent = '    '
        else:
            lines.append('package {')
            indent = '    '
        lines.append(f'{indent}public class {safe_cls} {{')

        # Constructor from iinit
        cidx = getattr(inst, 'iinit', 0)
        ctor_body = None
        if cidx and cidx < len(abc.methods):
            mb = method_bodies.get(cidx)
            if mb:
                try:
                    ctor_body = avm2.disassemble_instructions(pool, mb.code)
                except Exception as e:
                    ctor_body = f'// disasm failed: {e}'
        lines.append(f'{indent*2}public function {safe_cls}() {{')
        if ctor_body:
            lines.append(f'{indent*3}/* constructor disassembly:')
            for l in ctor_body.splitlines():
                lines.append(f'{indent*3}{l}')
            lines.append(f'{indent*3}*/')
        else:
            lines.append(f'{indent*3}// constructor body not available')
        lines.append(f'{indent*2}}}')
        lines.append('')

        # Instance traits (methods/getters/setters/slots)
        for t in inst.traits:
            kind = t.kind_flags & 0x0F
            # method-like
            if kind in (1, 2, 3):
                midx = getattr(t, 'method', None)
                if midx is None:
                    continue
                name = method_names.get(midx, f'method_{midx}')
                if kind == 2:
                    decl = f'public function get {name}():* {{'
                elif kind == 3:
                    decl = f'public function set {name}(v:*):void {{'
                else:
                    decl = f'public function {name}(...args):* {{'
                lines.append(f'{indent*2}// Trait kind={kind} method idx={midx}')
                lines.append(f'{indent*2}{decl}')
                mb = method_bodies.get(midx)
                if mb:
                    # First try flow recovery to produce pseudo-code
                    try:
                        from py_swf.tools.flow_recovery import recover_control_flow
                        pseudo = recover_control_flow(pool, mb.code)
                    except Exception:
                        pseudo = None
                    if pseudo:
                        lines.append(f'{indent*3}/* pseudo-code:')
                        for pl in pseudo.splitlines():
                            lines.append(f'{indent*3}{pl}')
                        lines.append(f'{indent*3}*/')
                        # also include raw disasm for reference
                        try:
                            d = avm2.disassemble_instructions(pool, mb.code)
                        except Exception as e:
                            d = f'// disasm failed: {e}'
                        lines.append(f'{indent*3}/* disassembly:')
                        for dl in d.splitlines():
                            lines.append(f'{indent*3}{dl}')
                        lines.append(f'{indent*3}*/')
                    else:
                        try:
                            d = avm2.disassemble_instructions(pool, mb.code)
                        except Exception as e:
                            d = f'// disasm failed: {e}'
                        lines.append(f'{indent*3}/* disassembly:')
                        for dl in d.splitlines():
                            lines.append(f'{indent*3}{dl}')
                        lines.append(f'{indent*3}*/')
                else:
                    lines.append(f'{indent*3}// no method body')
                # Close
                if kind in (2, 3):
                    lines.append(f'{indent*2}}}')
                else:
                    lines.append(f'{indent*2}    // TODO: reconstruct high-level body')
                    lines.append(f'{indent*2}}}')
                lines.append('')
            else:
                # other trait kinds: slot/property
                if getattr(t, 'type_name', 0):
                    prop_name = avm2.resolve_multiname(pool, t.name) if t.name else f'prop_{t.name}'
                    lines.append(f'{indent*2}// slot/property: {prop_name}')

        # Static initializer (cinit) from classes list
        if idx < len(abc.classes):
            class_info = abc.classes[idx]
            cinit_idx = getattr(class_info, 'cinit', None)
            if cinit_idx is not None and cinit_idx in method_bodies:
                mb = method_bodies[cinit_idx]
                try:
                    static_d = avm2.disassemble_instructions(pool, mb.code)
                except Exception as e:
                    static_d = f'// disasm failed: {e}'
                lines.append(f'{indent*2}// static initializer (cinit)')
                lines.append(f'{indent*2}/*')
                for sd in static_d.splitlines():
                    lines.append(f'{indent*2}{sd}')
                lines.append(f'{indent*2}*/')

        lines.append(f'{indent}}}')
        lines.append('}')

        files[filename] = '\n'.join(lines)

    # add index
    idx_lines = ['// Decompiled module index', 'package {', '    // Classes:']
    for fn in sorted(files.keys()):
        idx_lines.append(f'    // - {fn}')
    idx_lines.append('}')
    files['module_index.txt'] = '\n'.join(idx_lines)

    return files
