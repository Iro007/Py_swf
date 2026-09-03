from py_swf.tools.stack_sim import extract_conditions_from_lines


def test_extract_unary_condition():
    lines = [
        'pushint 0',
        'ifeq L_10'
    ]
    conds = extract_conditions_from_lines(lines)
    # conditional at index 1
    assert 1 in conds
    assert conds[1] == '(0 == 0)'


def test_extract_binary_condition():
    lines = [
        'pushint 2',
        'pushint 5',
        'iflt L_20'
    ]
    conds = extract_conditions_from_lines(lines)
    assert 2 in conds
    assert conds[2] == '(2 < 5)'
