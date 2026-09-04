from py_swf.tools.stack_sim import extract_conditions_from_lines


def test_lookupswitch_and_callproperty():
    lines = [
        'pushint 3',
        'pushint 1',
        'getlocal0',
        'lookupswitch L_default 2 [L_a, L_b]',
        'L_a:',
        'pushint 5',
        'callproperty myMethod 2',
        'L_b:',
        'pushint 7',
        'callproperty other 1',
        'L_default:',
        'pushint 0',
    ]
    conds = extract_conditions_from_lines(lines)
    # lookupswitch should produce a switch marker at its line
    keys = list(conds.keys())
    assert any('switch' in conds[k] for k in keys)


def test_binary_and_unary_conditions():
    lines = [
        'pushint 10',
        'getlocal 1',
        'iflt L_1',
        'pushint 0',
        'ifeq L_2',
    ]
    conds = extract_conditions_from_lines(lines)
    # must detect conditions for both iflt and ifeq
    assert any('<' in v for v in conds.values())
    assert any('==' in v or '!=' in v or '!' in v for v in conds.values())
