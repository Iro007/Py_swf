"""FastAPI endpoint tests over a synthetic in-memory SWF."""
import pytest
from fastapi.testclient import TestClient

from py_swf.swf_parser import SWFTag
from server.app import app
from tests.conftest import make_synthetic_swf
from tests.test_swf import _build_triangle_shape_tag

client = TestClient(app)

@pytest.fixture()
def session_id():
    swf_bytes = make_synthetic_swf([_build_triangle_shape_tag()])
    resp = client.post("/api/files", files={"file": ("test.swf", swf_bytes)})
    assert resp.status_code == 200, resp.text
    return resp.json()["session_id"]

def test_upload_reports_header(session_id):
    info = client.get(f"/api/files/{session_id}").json()
    assert info["signature"] == "FWS"
    assert info["frame_rate"] == 24.0
    assert info["width"] == 100.0

def test_list_tags(session_id):
    tags = client.get(f"/api/files/{session_id}/tags").json()
    assert tags[0]["name"] == "DefineShape"
    assert tags[0]["char_id"] == 1
    assert tags[-1]["name"] == "End"

def test_raw_slice(session_id):
    resp = client.get(f"/api/files/{session_id}/tags/0/raw", params={"offset": 0, "length": 2})
    assert resp.content == (1).to_bytes(2, "little")

def test_download_byte_identical(session_id):
    original = make_synthetic_swf([_build_triangle_shape_tag()])
    resp = client.get(f"/api/files/{session_id}/download")
    assert resp.content == original

def _doaction_tag():
    from py_swf.avm1 import assemble_avm1
    return SWFTag(12, assemble_avm1('push "hola"\ntrace\nend'))

def test_disassemble_and_assemble_avm1():
    swf_bytes = make_synthetic_swf([_doaction_tag()])
    sid = client.post("/api/files", files={"file": ("t.swf", swf_bytes)}).json()["session_id"]
    listing = client.get(f"/api/files/{sid}/tags/0/disassemble").json()
    assert listing["kind"] == "avm1"
    assert 'push "hola"' in listing["scripts"][0]["code"]

    new_code = listing["scripts"][0]["code"].replace("hola", "adios")
    resp = client.post(f"/api/files/{sid}/tags/0/assemble", json={"body_index": 0, "code": new_code})
    assert resp.status_code == 200, resp.text
    listing2 = client.get(f"/api/files/{sid}/tags/0/disassemble").json()
    assert 'push "adios"' in listing2["scripts"][0]["code"]

def test_assemble_bad_code_422():
    swf_bytes = make_synthetic_swf([_doaction_tag()])
    sid = client.post("/api/files", files={"file": ("t.swf", swf_bytes)}).json()["session_id"]
    resp = client.post(f"/api/files/{sid}/tags/0/assemble", json={"code": "no_such_op"})
    assert resp.status_code == 422

def test_export_svg(session_id):
    resp = client.get(f"/api/files/{session_id}/tags/0/export/svg")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("image/svg")
    assert "<svg" in resp.text

def test_export_image_roundtrip():
    import io
    from PIL import Image
    from py_swf.resources import replace_image

    seed = SWFTag(36, (7).to_bytes(2, "little") + b"\x05" + b"\x00" * 5)
    img = Image.new("RGBA", (2, 2), (0, 128, 255, 255))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    tag = replace_image(seed, buf.getvalue(), "png")

    swf_bytes = make_synthetic_swf([tag])
    sid = client.post("/api/files", files={"file": ("img.swf", swf_bytes)}).json()["session_id"]
    resp = client.get(f"/api/files/{sid}/tags/0/export/image")
    assert resp.status_code == 200
    out = Image.open(io.BytesIO(resp.content))
    assert out.getpixel((0, 0)) == (0, 128, 255, 255)

def test_put_raw_marks_dirty(session_id):
    resp = client.request(
        "PUT",
        f"/api/files/{session_id}/tags/0/raw",
        content=b"\x01\x02",
        headers={"Content-Type": "application/octet-stream"},
    )
    assert resp.status_code == 200
    assert resp.json()["new_size"] == 2

def test_unknown_session_404():
    assert client.get("/api/files/nope/tags").status_code == 404

def test_bad_upload_422():
    resp = client.post("/api/files", files={"file": ("x.swf", b"not a swf")})
    assert resp.status_code == 422
