from py_swf.avm2 import ConstantPool, assemble_instructions, disassemble_instructions


def roundtrip_and_check(text, contains=None):
    pool = ConstantPool()
    code = assemble_instructions(pool, text)
    out = disassemble_instructions(pool, code)
    if contains:
        for c in contains:
            assert c in out, f"Expected '{c}' in disassembly output:\n{out}"
    return out


def test_various_opcodes_roundtrip():
    text = '''
    pushint 123
    pushstring "test-string"
    getlocal 0
    setlocal 1
    getproperty com.example::prop
    setproperty com.example::prop
    callproperty com.example::method 1
    callpropvoid com.example::method 0
    returnvoid
    '''
    out = roundtrip_and_check(text, contains=["pushint", "pushstring", "getlocal", "setlocal", "getproperty", "setproperty", "callproperty", "callpropvoid"])


def test_lookupswitch_roundtrip():
    text = '''
    L_start:
    pushint 1
    lookupswitch L_case0 1 [L_case0]
    L_case0:
    returnvoid
    '''
    # Disassembly may normalize labels to numeric L_<pc> names; ensure lookupswitch exists and returns present
    out = roundtrip_and_check(text, contains=["lookupswitch", "returnvoid"])
    assert "L_" in out, f"Expected numeric label in disassembly, got:\n{out}"
