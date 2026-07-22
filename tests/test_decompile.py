"""Tests del decompilador v1 (AS3 outline, AVM2 method, AVM1)."""
import pytest

from py_swf.avm1 import assemble_avm1
from py_swf.avm2 import ABCFile, build_method_mapping
from py_swf.decompile import as3_outline, avm1_dec, avm2_dec
from py_swf.swf_parser import SWFFile
from tests.conftest import JPEXS_TESTDATA


def test_avm1_linear_code():
    asm = (
        'push "greeting" "hola"\n'
        "set_variable\n"
        'push "greeting"\n'
        "get_variable\n"
        "trace\n"
        "end"
    )
    src, err = avm1_dec.decompile_avm1(assemble_avm1(asm))
    assert err is None
    assert "greeting = \"hola\";" in src
    assert "trace(greeting);" in src


def test_avm1_arithmetic():
    asm = (
        'push "x" 3 4\n'
        "add\n"
        "set_variable\n"
        "end"
    )
    src, _ = avm1_dec.decompile_avm1(assemble_avm1(asm))
    assert "x = (3 + 4);" in src


@pytest.mark.skipif(not JPEXS_TESTDATA.is_dir(), reason="no corpus")
def test_as3_outline_from_corpus():
    path = JPEXS_TESTDATA / "as3" / "as3.swf"
    if not path.is_file():
        pytest.skip("as3.swf not present")
    swf = SWFFile()
    swf.read_bytes(path.read_bytes())
    abc = None
    for tag in swf.tags:
        if tag.is_doabc:
            _, _, ab = tag.parse_doabc()
            abc = ABCFile()
            abc.parse(ab)
            break
    assert abc is not None
    outline = as3_outline.outline_abc(abc)
    assert "package" in outline
    assert "class TestClass2" in outline
    assert "function" in outline


@pytest.mark.skipif(not JPEXS_TESTDATA.is_dir(), reason="no corpus")
def test_avm2_decompile_falls_back_gracefully():
    path = JPEXS_TESTDATA / "as3" / "as3.swf"
    if not path.is_file():
        pytest.skip("as3.swf not present")
    swf = SWFFile()
    swf.read_bytes(path.read_bytes())
    abc = None
    for tag in swf.tags:
        if tag.is_doabc:
            _, _, ab = tag.parse_doabc()
            abc = ABCFile()
            abc.parse(ab)
            break
    decompiled = 0
    for mb in abc.method_bodies:
        source, error = avm2_dec.decompile_method(abc, mb)
        # cada método o decompila o devuelve una razón de fallback, nunca crashea
        assert (source is None) == (error is not None)
        if source is not None:
            decompiled += 1
    assert decompiled > 0  # algunos métodos simples deben decompilar
