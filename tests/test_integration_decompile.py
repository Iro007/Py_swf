import subprocess
import sys
import os
import base64

PY = sys.executable
SCRIPT = os.path.join(os.path.dirname(__file__), '..', 'py_swf', 'tools', 'decompile_abc.py')

import py_swf.avm2 as avm2


def build_sample_abc():
    abc = avm2.ABCFile()
    pool = abc.constant_pool

    # Add strings
    name_idx = avm2.search_or_add_string(pool, 'MyClass')
    method_name_idx = avm2.search_or_add_string(pool, 'doSomething')

    # Add multiname for class (QName with empty namespace)
    mn_idx = avm2.search_or_add_multiname(pool, 'MyClass')

    # Create method
    m = avm2.MethodInfo()
    m.name = method_name_idx
    m.param_types = []
    m.return_type = 0
    m.flags = 0
    abc.methods.append(m)

    # Create method body with a simple pushint / pushint / iflt pattern and return
    # Use assemble_instructions to convert textual assembly to bytes
    asm = '''pushint 2
pushint 5
iflt L_10
pushint 0
L_10:
returnvoid
'''
    code = avm2.assemble_instructions(pool, asm)

    mb = avm2.MethodBodyInfo()
    mb.method = 0
    mb.max_stack = 10
    mb.local_count = 1
    mb.init_scope_depth = 1
    mb.max_scope_depth = 1
    mb.code = code
    abc.method_bodies.append(mb)

    # Create instance that points to multiname and has iinit = 0 (constructor)
    inst = avm2.InstanceInfo()
    inst.name = mn_idx
    inst.super_name = 0
    inst.flags = 0
    inst.iinit = 0
    inst.traits = []
    abc.instances.append(inst)

    # classes list must match instances length
    cls = avm2.ClassInfo()
    cls.cinit = 0
    cls.traits = []
    abc.classes.append(cls)

    # scripts empty
    return abc


def test_decompile_sample_abc_outputs_class_and_method(tmp_path):
    abc = build_sample_abc()
    abc_bytes = abc.serialize()
    b64 = base64.b64encode(abc_bytes).decode('ascii')

    p = subprocess.run([PY, SCRIPT, b64], capture_output=True, timeout=10)
    assert p.returncode == 0, f'stdout: {p.stdout}\nstderr: {p.stderr}'
    out = p.stdout.decode('utf8', errors='ignore')
    assert 'MyClass' in out
    assert 'doSomething' in out or 'method_0' in out
    assert 'disassembly' in out or 'pseudo-code' in out
