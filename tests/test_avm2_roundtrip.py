import py_swf.avm2 as avm2
from py_swf.avm2 import assemble_instructions, disassemble_instructions
from py_swf.avm2 import search_or_add_multiname


def run_roundtrip(text):
    abc = avm2.ABCFile()
    pool = abc.constant_pool
    code = assemble_instructions(pool, text)
    disasm = disassemble_instructions(pool, code)
    return disasm


def test_simple_push_and_call():
    text = '''
    pushint 42
    pushstring "hello"
    getlocal 0
    callproperty com.example::myMethod 1
    returnvoid
    '''
    d = run_roundtrip(text)
    assert 'pushint' in d
    assert 'pushstring' in d
    assert 'callproperty' in d.lower() or 'callproperty' in d


def test_lookupswitch_roundtrip():
    text = '''
    pushint 0
    lookupswitch L_default 1 [L_a]
    L_a:
      pushint 5
      returnvoid
    L_default:
      pushint 0
      returnvoid
    '''
    d = run_roundtrip(text)
    assert 'lookupswitch' in d


def test_callproperty_args_and_return():
    text = '''
    pushint 1
    pushint 2
    pushint 3
    callproperty com.example::sum 2
    returnvalue
    '''
    d = run_roundtrip(text)
    assert 'callproperty' in d
    assert 'return' in d
