from fastapi import APIRouter, Body, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from py_swf import morph, resources, shapes, sounds, text_fonts, timeline
from py_swf.avm1 import assemble_avm1, disassemble_avm1
from py_swf.avm2 import ABCFile, assemble_instructions, build_method_mapping, disassemble_instructions
from py_swf.decompile import as3_outline, avm1_dec, avm2_dec
from py_swf.swf_parser import SWFTag

from .files import get_session, get_tag

router = APIRouter(prefix="/api/files", tags=["export"])

IMAGE_TAGS = {6, 20, 21, 35, 36, 90}
SHAPE_TAGS = {2, 22, 32, 83}
SCRIPT_TAGS = {12, 59, 82}

class ScriptBody(BaseModel):
    body_index: int
    name: str
    code: str

class ScriptListing(BaseModel):
    kind: str
    scripts: list[ScriptBody]

class AssembleRequest(BaseModel):
    body_index: int = 0
    code: str

def _avm1_payload_offset(tag):
    # DoInitAction (59) payload starts with a UI16 sprite id before the actions
    return 2 if tag.tag_type == 59 else 0

def _parse_abc(tag):
    parsed = tag.parse_doabc()
    if parsed is None:
        raise HTTPException(status_code=422, detail="Malformed DoABC tag")
    flags, name, abc_bytes = parsed
    abc = ABCFile()
    try:
        abc.parse(abc_bytes)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"ABC parse failed: {exc}")
    return flags, name, abc

def _pack_doabc(flags, name, abc):
    payload = flags.to_bytes(4, "little") + name.encode("utf-8") + b"\x00" + abc.serialize()
    return payload

@router.get("/{sid}/tags/{index}/export/image")
def export_image(sid: str, index: int):
    session = get_session(sid)
    tag = get_tag(session, index)
    if tag.tag_type not in IMAGE_TAGS:
        raise HTTPException(status_code=422, detail="Not an image tag")
    jpeg_tables = resources.find_jpeg_tables(session.swf.tags) if tag.tag_type == 6 else None
    data, ext = resources.export_image(tag, jpeg_tables=jpeg_tables)
    if data is None:
        raise HTTPException(status_code=422, detail="Could not decode image")
    media = "image/png" if ext == "png" else "image/jpeg"
    return Response(content=data, media_type=media)

@router.get("/{sid}/tags/{index}/export/sound")
def export_sound(sid: str, index: int):
    tag = get_tag(get_session(sid), index)
    if tag.tag_type != 14:
        raise HTTPException(status_code=422, detail="Not a DefineSound tag")
    data, ext = sounds.export_sound(tag)
    if data is None:
        raise HTTPException(status_code=422, detail="Could not decode sound")
    media = {"mp3": "audio/mpeg", "wav": "audio/wav"}.get(ext, "application/octet-stream")
    return Response(content=data, media_type=media)

@router.get("/{sid}/tags/{index}/sound-info")
def sound_info(sid: str, index: int):
    tag = get_tag(get_session(sid), index)
    if tag.tag_type != 14:
        raise HTTPException(status_code=422, detail="Not a DefineSound tag")
    info = sounds.parse_define_sound(tag)
    if info is None:
        raise HTTPException(status_code=422, detail="Malformed DefineSound")
    info.pop("data")
    return info

@router.get("/{sid}/export/stream-sound")
def export_stream_sound(sid: str):
    session = get_session(sid)
    data, ext, _info = sounds.export_stream_sound(session.swf.tags)
    if data is None:
        raise HTTPException(status_code=422, detail="No MP3 stream sound in this file")
    return Response(content=data, media_type="audio/mpeg")

@router.get("/{sid}/tags/{index}/export/font")
def export_font(sid: str, index: int):
    tag = get_tag(get_session(sid), index)
    font = text_fonts.parse_font(tag)
    if font is None:
        raise HTTPException(status_code=422, detail="Not a supported font tag (DefineFont2/3)")
    svg = text_fonts.font_to_svg(font)
    return Response(content=svg, media_type="image/svg+xml")

@router.get("/{sid}/tags/{index}/font-info")
def font_info(sid: str, index: int):
    tag = get_tag(get_session(sid), index)
    font = text_fonts.parse_font(tag)
    if font is None:
        raise HTTPException(status_code=422, detail="Not a supported font tag (DefineFont2/3)")
    return {
        "font_id": font["font_id"],
        "name": font["name"],
        "italic": font["italic"],
        "bold": font["bold"],
        "num_glyphs": font["num_glyphs"],
        "codes": font["codes"],
        "layout": font["layout"],
    }

@router.get("/{sid}/tags/{index}/export/text-svg")
def export_text_svg(sid: str, index: int):
    session = get_session(sid)
    tag = get_tag(session, index)
    text = text_fonts.parse_text_tag(tag)
    if text is None:
        raise HTTPException(status_code=422, detail="Not a DefineText tag")
    fonts = text_fonts.collect_fonts(session.swf.tags)
    svg = text_fonts.text_to_svg(text, fonts)
    return Response(content=svg, media_type="image/svg+xml")

@router.get("/{sid}/tags/{index}/edit-text")
def edit_text_info(sid: str, index: int):
    tag = get_tag(get_session(sid), index)
    info = text_fonts.parse_edit_text(tag)
    if info is None:
        raise HTTPException(status_code=422, detail="Not a DefineEditText tag")
    return info

def make_bitmap_resolver(swf_tags):
    """Resolver de bitmap fills: char_id -> (png_bytes, width, height)."""
    import io

    from PIL import Image

    jpeg_tables = resources.find_jpeg_tables(swf_tags)
    by_id = {t.char_id: t for t in swf_tags if t.tag_type in IMAGE_TAGS and t.char_id is not None}

    def resolve(char_id):
        tag = by_id.get(char_id)
        if tag is None:
            return None
        data, ext = resources.export_image(tag, jpeg_tables=jpeg_tables)
        if data is None:
            return None
        try:
            img = Image.open(io.BytesIO(data))
            if ext != "png":
                buf = io.BytesIO()
                img.save(buf, "PNG")
                data = buf.getvalue()
            return data, img.width, img.height
        except Exception:
            return None

    return resolve

@router.get("/{sid}/tags/{index}/export/svg")
def export_svg(sid: str, index: int, ratio: float = 0.0):
    session = get_session(sid)
    tag = get_tag(session, index)
    try:
        if tag.tag_type in morph.MORPH_TAG_TYPES:
            svg = morph.morph_to_svg(tag, ratio=ratio)
        elif tag.tag_type in SHAPE_TAGS:
            svg = shapes.shape_to_svg(tag, bitmap_resolver=make_bitmap_resolver(session.swf.tags))
        else:
            raise HTTPException(status_code=422, detail="Not a shape tag")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Shape parse failed: {exc}")
    return Response(content=svg, media_type="image/svg+xml")

@router.get("/{sid}/timeline")
def timeline_info(sid: str):
    session = get_session(sid)
    frames = timeline.build_timeline(session.swf.tags)
    return {"frame_count": len(frames)}

@router.get("/{sid}/frames/{frame}/svg")
def frame_svg(sid: str, frame: int):
    session = get_session(sid)
    svg, count = timeline.render_frame(
        session.swf, frame, bitmap_resolver=make_bitmap_resolver(session.swf.tags)
    )
    if svg is None:
        raise HTTPException(status_code=422, detail="No frames in this file")
    return Response(content=svg, media_type="image/svg+xml", headers={"X-Frame-Count": str(count)})

@router.get("/{sid}/tags/{index}/sprite-frames/{frame}/svg")
def sprite_frame_svg(sid: str, index: int, frame: int):
    session = get_session(sid)
    tag = get_tag(session, index)
    if tag.tag_type != 39:
        raise HTTPException(status_code=422, detail="Not a DefineSprite tag")
    svg, count = timeline.render_sprite_frame(
        session.swf, tag, frame, bitmap_resolver=make_bitmap_resolver(session.swf.tags)
    )
    if svg is None:
        raise HTTPException(status_code=422, detail="Sprite has no frames")
    return Response(content=svg, media_type="image/svg+xml", headers={"X-Frame-Count": str(count)})

@router.get("/{sid}/tags/{index}/sprite-info")
def sprite_info(sid: str, index: int):
    tag = get_tag(get_session(sid), index)
    parsed = timeline.parse_sprite(tag)
    if not parsed:
        raise HTTPException(status_code=422, detail="Not a DefineSprite tag")
    char_id, declared_frames, inner = parsed
    frames = timeline.build_timeline(inner)
    return {"char_id": char_id, "declared_frames": declared_frames, "frame_count": len(frames)}

@router.get("/{sid}/tags/{index}/disassemble", response_model=ScriptListing)
def disassemble(sid: str, index: int):
    tag = get_tag(get_session(sid), index)
    if tag.tag_type in (12, 59):
        offset = _avm1_payload_offset(tag)
        code = disassemble_avm1(tag.data[offset:])
        return ScriptListing(kind="avm1", scripts=[ScriptBody(body_index=0, name=tag.name, code=code)])
    if tag.tag_type == 82:
        _, name, abc = _parse_abc(tag)
        mapping = build_method_mapping(abc)
        scripts = []
        for i, mb in enumerate(abc.method_bodies):
            method_name = mapping.get(mb.method, f"method_{mb.method}")
            code = disassemble_instructions(abc.constant_pool, mb.code)
            scripts.append(ScriptBody(body_index=i, name=method_name, code=code))
        return ScriptListing(kind="avm2", scripts=scripts)
    raise HTTPException(status_code=422, detail="Not a script tag")

@router.get("/{sid}/tags/{index}/decompile")
def decompile(sid: str, index: int):
    tag = get_tag(get_session(sid), index)
    if tag.tag_type in (12, 59):
        offset = _avm1_payload_offset(tag)
        source, error = avm1_dec.decompile_avm1(tag.data[offset:])
        return {
            "kind": "avm1",
            "sections": [{"name": tag.name, "source": source, "error": error}],
        }
    if tag.tag_type == 82:
        _, name, abc = _parse_abc(tag)
        mapping = build_method_mapping(abc)
        outline = as3_outline.outline_abc(abc)
        sections = [{"name": "// Class outline", "source": outline, "error": None}]
        for i, mb in enumerate(abc.method_bodies):
            method_name = mapping.get(mb.method, f"method_{mb.method}")
            source, error = avm2_dec.decompile_method(abc, mb, method_name)
            if source is None:
                source = f"// no decompilable ({error}); ver disassembly\n"
                source += disassemble_instructions(abc.constant_pool, mb.code)
            sections.append({
                "name": method_name,
                "source": f"// {method_name}\n{source}",
                "error": error,
            })
        return {"kind": "avm2", "sections": sections}
    raise HTTPException(status_code=422, detail="Not a script tag")

@router.post("/{sid}/tags/{index}/assemble")
def assemble(sid: str, index: int, req: AssembleRequest):
    session = get_session(sid)
    tag = get_tag(session, index)
    try:
        if tag.tag_type in (12, 59):
            offset = _avm1_payload_offset(tag)
            new_code = assemble_avm1(req.code)
            tag.data = tag.data[:offset] + new_code
        elif tag.tag_type == 82:
            flags, name, abc = _parse_abc(tag)
            if not (0 <= req.body_index < len(abc.method_bodies)):
                raise HTTPException(status_code=404, detail="Method body index out of range")
            abc.method_bodies[req.body_index].code = assemble_instructions(abc.constant_pool, req.code)
            tag.data = _pack_doabc(flags, name, abc)
        else:
            raise HTTPException(status_code=422, detail="Not a script tag")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Assembly failed: {exc}")
    session.dirty = True
    return {"ok": True, "new_size": len(tag.data)}

@router.post("/{sid}/tags/{index}/replace")
async def replace(sid: str, index: int, file: UploadFile):
    session = get_session(sid)
    tag = get_tag(session, index)
    data = await file.read()
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if tag.tag_type in IMAGE_TAGS:
        try:
            new_tag = resources.replace_image(tag, data, ext)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        session.swf.tags[index] = new_tag
    else:
        tag.data = data
    session.dirty = True
    return {"ok": True, "new_size": len(session.swf.tags[index].data)}

@router.put("/{sid}/tags/{index}/raw")
async def put_raw(sid: str, index: int, body: bytes = Body(..., media_type="application/octet-stream")):
    session = get_session(sid)
    tag = get_tag(session, index)
    tag.data = body
    session.dirty = True
    return {"ok": True, "new_size": len(tag.data)}
