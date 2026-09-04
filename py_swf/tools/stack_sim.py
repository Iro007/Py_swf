"""A tiny symbolic stack simulator for AVM2 disassembly lines.
Provides conservative extraction of condition expressions at conditional instructions.

API:
- extract_conditions_from_lines(lines) -> dict[line_index] = condition_str

This is intentionally simple and conservative.
"""
from typing import List, Dict

# Mapping of conditional mnemonics that compare two values
BINARY_CONDS = set([
    'iflt', 'ifge', 'ifgt', 'ifle', 'ifnlt', 'ifnge', 'ifngt', 'ifnle',
    'ifstricteq', 'ifstrictne', 'iflt_u', 'ifge_u'
])

# Single-value conditionals (compare to zero)
UNARY_CONDS = set(['ifeq', 'ifne', 'iftrue', 'iffalse'])

# Additional mnemonics that behave like pushes
PUSH_LIKE = set(['getlex', 'getproperty', 'findproperty', 'findpropstrict', 'getslot'])


def _parse_instr(line: str):
    parts = line.strip().split()
    if not parts:
        return None, []
    return parts[0], parts[1:]


def extract_conditions_from_lines(lines: List[str]) -> Dict[int, str]:
    """Return a mapping from line index (where conditional mnemonic occurs) to a human-friendly condition string.

    Heuristics:
    - pushint N, pushuint N, pushdouble N, pushstring "s" push literal onto stack
    - getlocal N -> localN
    - getlocal0/1 style handled if mnemonic is 'getlocal' with arg or 'getlocal0'
    - binary cond: pop b, pop a -> produce 'a < b' etc.
    - unary cond: pop v -> produce 'v == 0' or 'v != 0'

    Conservative: if not enough stack info, fall back to generic comments.
    """
    stack: List[str] = []
    conds: Dict[int, str] = {}

    for i, ln in enumerate(lines):
        mnemonic, args = _parse_instr(ln)
        if mnemonic is None:
            continue

        # push* instructions
        if mnemonic in ('pushint', 'pushuint', 'pushdouble') and args:
            stack.append(args[0])
            continue
        if mnemonic == 'pushstring' and args:
            # join the rest as string literal
            s = ' '.join(args)
            stack.append(s)
            continue

        # getlocal or getlocalX
        if mnemonic.startswith('getlocal'):
            # getlocalN like 'getlocal0' or 'getlocal 0'
            idx = None
            if mnemonic == 'getlocal' and args:
                idx = args[0]
            else:
                # trailing digits
                suffix = mnemonic[len('getlocal'):]
                if suffix.isdigit():
                    idx = suffix
            name = f'local{idx}' if idx is not None else 'local'
            stack.append(name)
            continue

        # getlex/getproperty/getslot push reference (symbolic)
        if mnemonic in PUSH_LIKE or mnemonic == 'getlocal0':
            if args:
                stack.append(' '.join(args))
            else:
                stack.append('value')
            continue

        # try to handle pushscope/pushwith as neutral (no stack effect tracked)
        if mnemonic in ('pushscope', 'pushwith', 'popscope'):
            continue

        # support returnvalue/returnvoid as terminators (no stack push)
        if mnemonic in ('returnvalue', 'returnvoid'):
            stack.clear()
            continue

        # lookupswitch: pop a key and produce a 'switch' style condition marker
        if mnemonic == 'lookupswitch' or mnemonic.startswith('lookupswitch'):
            # conservative: consume one key and push a symbolic result
            if stack:
                key = stack.pop()
            else:
                key = 'key'
            # we won't try to reconstruct cases here; just note a switch occurred
            conds[i] = f'(switch on {key})'
            # push placeholder result of switch
            stack.append('switch_result')
            continue

        # lookupswitch: pop a key and produce a 'switch' style condition marker
        if mnemonic == 'lookupswitch' or mnemonic.startswith('lookupswitch'):
            # conservative: consume one key and push a symbolic result
            if stack:
                key = stack.pop()
            else:
                key = 'key'
            # we won't try to reconstruct cases here; just note a switch occurred
            conds[i] = f'(switch on {key})'
            # push placeholder result of switch
            stack.append('switch_result')
            continue

        # conditional binary
        if mnemonic in BINARY_CONDS:
            # try to pop two items
            if len(stack) >= 2:
                b = stack.pop()
                a = stack.pop()
                op = {
                    'iflt': '<', 'ifnge': '>=', 'ifngt': '>', 'ifnle': '<=',
                    'ifge': '>=', 'ifgt': '>', 'ifle': '<=',
                }.get(mnemonic, '==')
                conds[i] = f'({a} {op} {b})'
            else:
                conds[i] = '(cond?)'
            # conditional consumes operands
            continue

        # conditional unary
        if mnemonic in UNARY_CONDS:
            if stack:
                v = stack.pop()
                if mnemonic == 'ifeq':
                    conds[i] = f'({v} == 0)'
                elif mnemonic == 'ifne':
                    conds[i] = f'({v} != 0)'
                elif mnemonic == 'iftrue':
                    conds[i] = f'({v})'
                elif mnemonic == 'iffalse':
                    conds[i] = f'(!{v})'
            else:
                conds[i] = '(cond?)'
            continue

        # other ops that pop known counts (callproperty, callmethod, callstatic) -- approximate
        if mnemonic.startswith('call') and args:
            # callproperty <multiname> <arg_count>
            # many callers use arg_count as last arg; try to parse
            try:
                arg_count = int(args[-1])
            except Exception:
                # some disassemblers show callproperty <multiname> [arg_count]
                arg_count = 0
                # try to find a numeric arg in args
                for a in reversed(args):
                    try:
                        arg_count = int(a)
                        break
                    except Exception:
                        continue
            # pop args + target (for callproperty the target object is also on stack)
            total_pops = arg_count + (1 if mnemonic == 'callproperty' else 0)
            for _ in range(total_pops):
                if stack:
                    stack.pop()
            # push return value placeholder
            stack.append('ret')
            continue

        # default: keep going; some ops like pushscope, pushwith ignored
        # ops that push are not handled exhaustively

    return conds
