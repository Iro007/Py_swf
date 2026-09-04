from py_swf.tools.flow_recovery import recover_control_flow
import py_swf.avm2 as avm2


def test_lookupswitch_recovery():
    pool = avm2.ConstantPool()
    # ensure string pool has base entries
    pool.strings = [""]

    # build a small assembly with a lookupswitch
    asm = '''
L_start:
    pushstring "key"
    lookupswitch L_default 1 [L_case0]
L_case0:
    pushint 1
    jump L_end
L_default:
    pushint 0
L_end:
    returnvoid
'''
    code = avm2.assemble_instructions(pool, asm)
    pseudo = recover_control_flow(pool, code)
    assert 'switch' in pseudo.lower() or 'switch on' in pseudo.lower()
    assert 'default' in pseudo.lower() or 'case' in pseudo.lower()
