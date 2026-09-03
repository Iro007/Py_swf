"""Simple flow recovery heuristics.
Produces a readable pseudo-code from method bytecode by using disassembly and
looking for conditional/backward jumps to detect simple if/while structures.
This is intentionally conservative: it produces annotated pseudo-code, not full
structured reconstruction.
"""
from typing import List
import py_swf.avm2 as avm2

COND_MNEMONICS = set([
    'iftrue', 'iffalse', 'ifeq', 'ifne', 'iflt', 'ifge', 'ifgt', 'ifle',
    'ifstricteq', 'ifstrictne', 'ifnlt', 'ifnge', 'ifngt', 'ifnle'
])
JUMP_MNEMONICS = set(['jump'])


def recover_control_flow(pool, code: bytes) -> str:
    """Return a conservative pseudo-code string for the given method code.
    Uses avm2.disassemble_instructions to obtain labeled assembly, then
    applies heuristics to identify forward conditionals and backward loops.
    """
    try:
        disasm = avm2.disassemble_instructions(pool, code)
    except Exception as e:
        return f'/* flow recovery failed: {e} */\n' + (getattr(e, 'args', [''])[0] if hasattr(e, 'args') else '')

    lines = disasm.splitlines()
    # Map label -> line index
    label_to_idx = {}
    for i, ln in enumerate(lines):
        ln = ln.strip()
        if ln.endswith(':') and ln.startswith('L_'):
            label_to_idx[ln[:-1]] = i

    pseudo: List[str] = []
    i = 0
    n = len(lines)
    # Precompute simple symbolic conditions using stack simulation
    try:
        from py_swf.tools.stack_sim import extract_conditions_from_lines
        cond_map = extract_conditions_from_lines(lines)
    except Exception:
        cond_map = {}

    while i < n:
        ln = lines[i]
        stripped = ln.strip()
        if not stripped:
            i += 1
            continue
        # Label
        if stripped.endswith(':') and stripped.startswith('L_'):
            pseudo.append(f'{stripped}')
            i += 1
            continue

        # Instruction
        parts = stripped.split()
        mnemonic = parts[0] if parts else ''

        # handle lookupswitch specially
        if mnemonic == 'lookupswitch' and len(parts) >= 4:
            # parts: lookupswitch DEFAULT LIMIT [L_a, L_b]
            default_lbl = parts[1]
            try:
                case_limit = int(parts[2])
            except Exception:
                case_limit = 0
            case_list_raw = parts[3]
            case_list_raw = case_list_raw.strip()
            if case_list_raw.startswith('[') and case_list_raw.endswith(']'):
                case_items = [c.strip() for c in case_list_raw[1:-1].split(',') if c.strip()]
            else:
                case_items = []

            pseudo.append(f'switch (/* key */) {{')
            # for each case label include a short body (heuristic)
            for lbl in case_items:
                pseudo.append(f'  case {lbl}:')
                j = label_to_idx.get(lbl, None)
                body_lines = []
                if j is not None:
                    k = j + 1
                    while k < n and not (lines[k].strip().startswith('L_')):
                        body_lines.append('    ' + lines[k].strip())
                        k += 1
                if not body_lines:
                    body_lines.append('    // (case body omitted)')
                pseudo.extend(body_lines)
                pseudo.append('    break;')
            # default
            pseudo.append(f'  default:')
            j = label_to_idx.get(default_lbl, None)
            if j is not None:
                k = j + 1
                body_lines = []
                while k < n and not (lines[k].strip().startswith('L_')):
                    body_lines.append('    ' + lines[k].strip())
                    k += 1
                if not body_lines:
                    body_lines.append('    // (default body omitted)')
                pseudo.extend(body_lines)
            else:
                pseudo.append('    // (default body omitted)')
            pseudo.append('}\n')
            i += 1


        # conditional
        if mnemonic in COND_MNEMONICS and len(parts) >= 2:
            target = parts[1]
            tgt_idx = label_to_idx.get(target, None)
            cond = cond_map.get(i)
            cond_text = cond if cond else '/* condition */'
            if tgt_idx is not None:
                # if target is before current => loop
                if tgt_idx < i:
                    pseudo.append(f'while {cond_text} {{')
                    # include body: from next line until we encounter the label target
                    j = i + 1
                    body_lines = []
                    while j < n and not (lines[j].strip() == target + ':'):
                        body_lines.append('    ' + lines[j].strip())
                        j += 1
                    if not body_lines:
                        body_lines.append('    // (loop body omitted)')
                    pseudo.extend(body_lines)
                    pseudo.append('    // loop continues; translated from backward branch')
                    pseudo.append('}\n')
                    i = j
                    continue
                else:
                    # forward conditional -> if
                    pseudo.append(f'if {cond_text} {{')
                    # include subsequent instructions until the target label
                    j = i + 1
                    body_lines = []
                    while j < n and not (lines[j].strip() == target + ':'):
                        body_lines.append('    ' + lines[j].strip())
                        j += 1
                    if not body_lines:
                        body_lines.append('    // (then body omitted)')
                    pseudo.extend(body_lines)
                    pseudo.append('}\n')
                    i = j
                    continue        # unconditional jump
        if mnemonic in JUMP_MNEMONICS and len(parts) >= 2:
            target = parts[1]
            tgt_idx = label_to_idx.get(target, None)
            if tgt_idx is not None:
                if tgt_idx < i:
                    pseudo.append('// goto backward -> likely loop')
                    pseudo.append(f'goto {target}')
                else:
                    pseudo.append(f'// goto {target}')
                i += 1
                continue

        # default: include instruction as comment to keep context
        pseudo.append('// ' + stripped)
        i += 1

    return '\n'.join(pseudo)
