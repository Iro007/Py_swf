import sys
import os

# Add parent directory to path so we can import py_swf
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from py_swf.swf_parser import SWFFile, SWFTag, make_rect, parse_rect, BitStream
from py_swf.avm1 import assemble_avm1, disassemble_avm1
from py_swf.avm2 import ConstantPool, MethodInfo, MethodBodyInfo, ABCFile, assemble_instructions, disassemble_instructions

def test_rect():
    print("Testing RECT bit packing/unpacking...")
    # Test values
    xmin, xmax, ymin, ymax = -20, 11000, -40, 8250
    rect_bytes = make_rect(xmin, xmax, ymin, ymax)
    
    stream = BitStream(rect_bytes)
    rect = parse_rect(stream)
    
    assert rect["xmin"] == xmin, f"Expected xmin={xmin}, got {rect['xmin']}"
    assert rect["xmax"] == xmax, f"Expected xmax={xmax}, got {rect['xmax']}"
    assert rect["ymin"] == ymin, f"Expected ymin={ymin}, got {rect['ymin']}"
    assert rect["ymax"] == ymax, f"Expected ymax={ymax}, got {rect['ymax']}"
    print("RECT test passed!")


def test_doabc_parse():
    print("Testing DoABC tag name parsing...")
    flags = 0x12345678
    name = "MyScript"
    payload = flags.to_bytes(4, "little") + name.encode("utf-8") + b"\x00" + b"\x00\x00\x00\x00"
    tag = SWFTag(82, payload)
    parsed = tag.parse_doabc()
    assert parsed is not None, "DoABC parsing returned None"
    parsed_flags, parsed_name, abc_data = parsed
    assert parsed_flags == flags, "DoABC flags parsed incorrectly"
    assert parsed_name == name, "DoABC name parsed incorrectly"
    assert abc_data == b"\x00\x00\x00\x00", "DoABC ABC data parsed incorrectly"
    print("DoABC parse test passed!")


def test_avm1_roundtrip():
    print("Testing AVM1 disassemble/assemble roundtrip...")
    # Simple script with a push, jump, variable assignment, and end
    assembly = (
        "    push \"my_variable\" 42\n"
        "    set_variable\n"
        "    get_variable\n"
        "    push 10\n"
        "    equals\n"
        "    if L_27\n"
        "    push \"not_equal\"\n"
        "    trace\n"
        "    jump L_31\n"
        "L_27:\n"
        "    push \"equal\"\n"
        "    trace\n"
        "L_31:\n"
        "    end"
    )
    
    # Assemble to bytes
    bytecode = assemble_avm1(assembly)
    print(f"AVM1 compiled bytecode length: {len(bytecode)} bytes")
    
    # Disassemble back to text
    disassembled = disassemble_avm1(bytecode)
    print("AVM1 Disassembly:")
    print(disassembled)
    
    # Re-assemble
    recompiled = assemble_avm1(disassembled)
    
    # Compare bytes
    assert bytecode == recompiled, "AVM1 Bytecode mismatch after roundtrip!"
    print("AVM1 roundtrip test passed!")

def test_avm2_roundtrip():
    print("Testing AVM2 disassemble/assemble roundtrip...")
    pool = ConstantPool()
    # Add initial standard elements
    pool.strings.append("trace")
    
    # Create simple assembly script
    assembly = (
        "    getlocal_0\n"
        "    pushscope\n"
        "    findpropstrict trace\n"
        "    pushstring \"Hello AVM2!\"\n"
        "    callpropvoid trace 1\n"
        "    returnvoid"
    )
    
    # Compile
    bytecode = assemble_instructions(pool, assembly)
    print(f"AVM2 compiled bytecode length: {len(bytecode)} bytes")
    
    # Disassemble
    disassembled = disassemble_instructions(pool, bytecode)
    print("AVM2 Disassembly:")
    print(disassembled)
    
    # Re-compile
    recompiled = assemble_instructions(pool, disassembled)
    
    # Compare
    assert bytecode == recompiled, "AVM2 Bytecode mismatch after roundtrip!"
    print("AVM2 roundtrip test passed!")


def test_doabc_edit_and_save():
    print("Testing DoABC edit and save roundtrip...")
    import tempfile
    from pathlib import Path

    pool = ConstantPool()
    pool.strings.append("trace")
    pool.strings.append("Hello AVM2!")

    method = MethodInfo()
    method.param_types = []
    method.return_type = 0
    method.name = 1
    method.flags = 0

    mb = MethodBodyInfo()
    mb.method = 0
    mb.max_stack = 10
    mb.local_count = 0
    mb.init_scope_depth = 1
    mb.max_scope_depth = 1
    mb.exceptions = []
    mb.traits = []
    mb.code = assemble_instructions(pool, "getlocal_0\nreturnvoid")

    abc = ABCFile()
    abc.constant_pool = pool
    abc.methods = [method]
    abc.metadata = []
    abc.instances = []
    abc.classes = []
    abc.scripts = []
    abc.method_bodies = [mb]

    abc_bytes = abc.serialize()
    payload = (0).to_bytes(4, "little") + b"MyABC\x00" + abc_bytes
    tag = SWFTag(82, payload)

    swf = SWFFile()
    swf.signature = "FWS"
    swf.version = 10
    swf.rect = {"xmin": 0, "xmax": 1100, "ymin": 0, "ymax": 900}
    swf.frame_rate = 12.0
    swf.frame_count = 1
    swf.tags = [tag]

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test_doabc.swf"
        swf.save_file(path)

        loaded = SWFFile()
        loaded.read_file(str(path))
        assert len(loaded.tags) == 2, "Saved SWF should include the DoABC tag and End tag"
        loaded_tag = loaded.tags[0]
        flags, name, loaded_abc_bytes = loaded_tag.parse_doabc()
        assert name == "MyABC", "DoABC name should survive save/load"

        reloaded_abc = ABCFile()
        reloaded_abc.parse(loaded_abc_bytes)
        assert len(reloaded_abc.method_bodies) == 1, "Loaded ABC should contain one method body"

        new_code = assemble_instructions(reloaded_abc.constant_pool, "getlocal_0\npushstring \"Updated\"\nreturnvoid")
        reloaded_abc.method_bodies[0].code = new_code
        updated_abc_bytes = reloaded_abc.serialize()

        updated_payload = (0).to_bytes(4, "little") + b"MyABC\x00" + updated_abc_bytes
        updated_tag = SWFTag(82, updated_payload)
        loaded.tags[0] = updated_tag

        path2 = Path(tmpdir) / "test_doabc_updated.swf"
        loaded.save_file(path2)

        reloaded = SWFFile()
        reloaded.read_file(str(path2))
        final_abc = ABCFile()
        final_abc.parse(reloaded.tags[0].parse_doabc()[2])
        assert final_abc.method_bodies[0].code == new_code, "Updated ABC code should be preserved after save"

    print("DoABC edit/save roundtrip test passed!")

def test_escaped_strings_compilation():
    print("Testing string compilation with spaces and escaped quotes...")
    
    # 1. AVM1 Test
    avm1_assembly = (
        '    push "Hello \\"world\\" from AVM1" "another spacey string"\n'
        '    end'
    )
    avm1_bytecode = assemble_avm1(avm1_assembly)
    avm1_disasm = disassemble_avm1(avm1_bytecode)
    assert 'push "Hello \\"world\\" from AVM1" "another spacey string"' in avm1_disasm, "AVM1 string mismatch"
    
    # 2. AVM2 Test
    pool = ConstantPool()
    avm2_assembly = (
        '    findpropstrict trace\n'
        '    pushstring "Hello \\"AVM2\\" world!"\n'
        '    callpropvoid trace 1\n'
        '    returnvoid'
    )
    avm2_bytecode = assemble_instructions(pool, avm2_assembly)
    avm2_disasm = disassemble_instructions(pool, avm2_bytecode)
    assert 'pushstring "Hello \\"AVM2\\" world!"' in avm2_disasm, "AVM2 string mismatch"
    
    print("String compilation tests passed!")

if __name__ == "__main__":
    test_rect()
    print("-" * 40)
    test_doabc_parse()
    print("-" * 40)
    test_avm1_roundtrip()
    print("-" * 40)
    test_avm2_roundtrip()
    print("-" * 40)
    test_doabc_edit_and_save()
    print("-" * 40)
    test_escaped_strings_compilation()
    print("=" * 40)
    print("All unit tests passed successfully!")
