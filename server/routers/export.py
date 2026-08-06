from fastapi import APIRouter, Body, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from py_swf import morph, resources, shapes, sounds, text_fonts, timeline, video, shape_edit, font_edit, fla_export, robust_parser
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


@router.get("/{sid}/tags/{index}/video-info")
def video_info(sid: str, index: int):
    tag = get_tag(get_session(sid), index)
    if tag.tag_type == 60:
        info = video.parse_video_stream(tag)
        if info is None:
            raise HTTPException(status_code=422, detail="Malformed DefineVideoStream")
        return info
    if tag.tag_type == 61:
        info = video.parse_video_frame(tag)
        if info is None:
            raise HTTPException(status_code=422, detail="Malformed VideoFrame")
        return info
    raise HTTPException(status_code=422, detail="Not a video tag")


@router.get("/{sid}/export/video")
def export_video(sid: str):
    session = get_session(sid)
    streams = video.export_video_frames(session.swf.tags)
    if not streams:
        raise HTTPException(status_code=422, detail="No video streams in this file")
    # Export first stream as FLV
    flv_data = video.export_to_flv(streams)
    if flv_data is None:
        raise HTTPException(status_code=422, detail="Could not encode video")
    return Response(content=flv_data, media_type="video/x-flv")


@router.get("/{sid}/export/video-info")
def export_video_info(sid: str):
    session = get_session(sid)
    streams = video.export_video_frames(session.swf.tags)
    return {"streams": streams}


class ShapeVertexUpdate(BaseModel):
    group_idx: int
    subpath_idx: int
    vertex_idx: int
    x: float
    y: float


class ShapeEdgeAdd(BaseModel):
    group_idx: int
    subpath_idx: int
    after_vertex_idx: int
    edge_type: str  # "line" or "curve"
    x: float
    y: float
    cx: float | None = None
    cy: float | None = None


class ShapeVertexDelete(BaseModel):
    group_idx: int
    subpath_idx: int
    vertex_idx: int


@router.get("/{sid}/tags/{index}/shape-data")
def get_shape_data(sid: str, index: int):
    session = get_session(sid)
    tag = get_tag(session, index)
    if tag.tag_type not in SHAPE_TAGS:
        raise HTTPException(status_code=422, detail="Not a shape tag")
    parsed = shapes.parse_shape_tag(tag)
    return parsed


@router.post("/{sid}/tags/{index}/shape/update-vertex")
def update_shape_vertex(sid: str, index: int, req: ShapeVertexUpdate):
    session = get_session(sid)
    tag = get_tag(session, index)
    if tag.tag_type not in SHAPE_TAGS:
        raise HTTPException(status_code=422, detail="Not a shape tag")
    parsed = shapes.parse_shape_tag(tag)
    try:
        shape_edit.update_shape_vertex(parsed, req.group_idx, req.subpath_idx, req.vertex_idx, req.x, req.y)
        new_tag = shape_edit.rebuild_shape_tag(parsed, tag.tag_type)
        session.swf.tags[index] = new_tag
        session.dirty = True
        return {"ok": True, "new_size": len(new_tag.data)}
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Shape update failed: {exc}")


@router.post("/{sid}/tags/{index}/shape/add-edge")
def add_shape_edge(sid: str, index: int, req: ShapeEdgeAdd):
    session = get_session(sid)
    tag = get_tag(session, index)
    if tag.tag_type not in SHAPE_TAGS:
        raise HTTPException(status_code=422, detail="Not a shape tag")
    parsed = shapes.parse_shape_tag(tag)
    try:
        shape_edit.add_shape_edge(parsed, req.group_idx, req.subpath_idx, req.after_vertex_idx, req.edge_type, req.x, req.y, req.cx, req.cy)
        new_tag = shape_edit.rebuild_shape_tag(parsed, tag.tag_type)
        session.swf.tags[index] = new_tag
        session.dirty = True
        return {"ok": True, "new_size": len(new_tag.data)}
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Shape add edge failed: {exc}")


@router.post("/{sid}/tags/{index}/shape/delete-vertex")
def delete_shape_vertex(sid: str, index: int, req: ShapeVertexDelete):
    session = get_session(sid)
    tag = get_tag(session, index)
    if tag.tag_type not in SHAPE_TAGS:
        raise HTTPException(status_code=422, detail="Not a shape tag")
    parsed = shapes.parse_shape_tag(tag)
    try:
        shape_edit.delete_shape_vertex(parsed, req.group_idx, req.subpath_idx, req.vertex_idx)
        new_tag = shape_edit.rebuild_shape_tag(parsed, tag.tag_type)
        session.swf.tags[index] = new_tag
        session.dirty = True
        return {"ok": True, "new_size": len(new_tag.data)}
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Shape delete vertex failed: {exc}")


# ===== Batch export =====

class BatchExportRequest(BaseModel):
    tag_indices: list[int]
    format: str = "png"  # png, svg, jpg


@router.post("/{sid}/batch-export/images")
async def batch_export_images(sid: str, req: BatchExportRequest):
    session = get_session(sid)
    results = []
    jpeg_tables = resources.find_jpeg_tables(session.swf.tags)
    
    for idx in req.tag_indices:
        if idx < 0 or idx >= len(session.swf.tags):
            results.append({"index": idx, "error": "Invalid tag index"})
            continue
        tag = session.swf.tags[idx]
        if tag.tag_type not in IMAGE_TAGS:
            results.append({"index": idx, "error": "Not an image tag"})
            continue
        
        try:
            data, ext = resources.export_image(tag, jpeg_tables=jpeg_tables)
            if data is None:
                results.append({"index": idx, "error": "Could not decode"})
                continue
            
            # Convert to requested format if needed
            if req.format != ext:
                import io
                from PIL import Image
                img = Image.open(io.BytesIO(data))
                buf = io.BytesIO()
                if req.format == "jpg" and img.mode in ("RGBA", "LA", "P"):
                    img = img.convert("RGB")
                img.save(buf, req.format.upper())
                data = buf.getvalue()
                ext = req.format
            
            import base64
            b64 = base64.b64encode(data).decode("ascii")
            results.append({
                "index": idx,
                "char_id": tag.char_id,
                "name": tag.name,
                "data": b64,
                "format": ext,
                "size": len(data),
            })
        except Exception as e:
            results.append({"index": idx, "error": str(e)})
    
    return {"results": results}


@router.post("/{sid}/batch-export/shapes")
async def batch_export_shapes(sid: str, req: BatchExportRequest):
    session = get_session(sid)
    results = []
    
    resolver = make_bitmap_resolver(session.swf.tags)
    
    for idx in req.tag_indices:
        if idx < 0 or idx >= len(session.swf.tags):
            results.append({"index": idx, "error": "Invalid tag index"})
            continue
        tag = session.swf.tags[idx]
        if tag.tag_type not in SHAPE_TAGS and tag.tag_type not in morph.MORPH_TAG_TYPES:
            results.append({"index": idx, "error": "Not a shape tag"})
            continue
        
        try:
            if tag.tag_type in morph.MORPH_TAG_TYPES:
                svg = morph.morph_to_svg(tag, ratio=0.0)
            else:
                svg = shapes.shape_to_svg(tag, bitmap_resolver=resolver)
            
            if req.format == "svg":
                data = svg.encode("utf-8")
            else:
                # For PNG/JPG, would need to rasterize SVG (requires external tool)
                # Return SVG as base64 for now
                import base64
                data = base64.b64encode(svg.encode("utf-8")).decode("ascii")
            
            results.append({
                "index": idx,
                "char_id": tag.char_id,
                "name": tag.name,
                "data": data if isinstance(data, str) else data.decode("utf-8"),
                "format": req.format if req.format == "svg" else "svg",
                "size": len(data) if isinstance(data, bytes) else len(data),
            })
        except Exception as e:
            results.append({"index": idx, "error": str(e)})
    
    return {"results": results}


@router.post("/{sid}/batch-export/scripts")
async def batch_export_scripts(sid: str, req: BatchExportRequest):
    session = get_session(sid)
    results = []
    
    for idx in req.tag_indices:
        if idx < 0 or idx >= len(session.swf.tags):
            results.append({"index": idx, "error": "Invalid tag index"})
            continue
        tag = session.swf.tags[idx]
        if tag.tag_type not in SCRIPT_TAGS:
            results.append({"index": idx, "error": "Not a script tag"})
            continue
        
        try:
            if tag.tag_type in (12, 59):
                offset = _avm1_payload_offset(tag)
                code = disassemble_avm1(tag.data[offset:])
                results.append({
                    "index": idx,
                    "kind": "avm1",
                    "code": code,
                    "format": "asm",
                })
            elif tag.tag_type == 82:
                _, name, abc = _parse_abc(tag)
                mapping = build_method_mapping(abc)
                all_code = []
                for i, mb in enumerate(abc.method_bodies):
                    method_name = mapping.get(mb.method, f"method_{mb.method}")
                    code = disassemble_instructions(abc.constant_pool, mb.code)
                    all_code.append(f"// {method_name}\n{code}")
                results.append({
                    "index": idx,
                    "kind": "avm2",
                    "code": "\n\n".join(all_code),
                    "format": "asm",
                })
        except Exception as e:
            results.append({"index": idx, "error": str(e)})
    
    return {"results": results}


@router.get("/{sid}/export/all-resources")
def export_all_resources(sid: str):
    """Export all images, shapes, sounds, fonts, scripts as a ZIP."""
    import zipfile
    import io
    import base64
    
    session = get_session(sid)
    buf = io.BytesIO()
    
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        jpeg_tables = resources.find_jpeg_tables(session.swf.tags)
        resolver = make_bitmap_resolver(session.swf.tags)
        
        for i, tag in enumerate(session.swf.tags):
            try:
                # Images
                if tag.tag_type in IMAGE_TAGS:
                    data, ext = resources.export_image(tag, jpeg_tables=jpeg_tables)
                    if data:
                        name = f"images/tag_{i}"
                        if tag.char_id:
                            name += f"_id{tag.char_id}"
                        if tag.symbol_name:
                            name += f"_{tag.symbol_name}"
                        name += f".{ext}"
                        zf.writestr(name, data)
                
                # Sounds
                elif tag.tag_type == 14:
                    data, ext = sounds.export_sound(tag)
                    if data:
                        name = f"sounds/tag_{i}"
                        if tag.char_id:
                            name += f"_id{tag.char_id}"
                        name += f".{ext}"
                        zf.writestr(name, data)
                
                # Fonts
                elif tag.tag_type in (48, 75):
                    font = text_fonts.parse_font(tag)
                    if font:
                        svg = text_fonts.font_to_svg(font)
                        name = f"fonts/tag_{i}"
                        if tag.char_id:
                            name += f"_id{tag.char_id}"
                        name += ".svg"
                        zf.writestr(name, svg.encode("utf-8"))
                
                # Scripts
                elif tag.tag_type in SCRIPT_TAGS:
                    if tag.tag_type in (12, 59):
                        offset = _avm1_payload_offset(tag)
                        code = disassemble_avm1(tag.data[offset:])
                        name = f"scripts/tag_{i}.as"
                        zf.writestr(name, code)
                    elif tag.tag_type == 82:
                        _, name_abc, abc = _parse_abc(tag)
                        mapping = build_method_mapping(abc)
                        all_code = []
                        for j, mb in enumerate(abc.method_bodies):
                            method_name = mapping.get(mb.method, f"method_{mb.method}")
                            code = disassemble_instructions(abc.constant_pool, mb.code)
                            all_code.append(f"// {method_name}\n{code}")
                        name = f"scripts/tag_{i}.as"
                        zf.writestr(name, "\n\n".join(all_code))
                
                # Shapes
                elif tag.tag_type in SHAPE_TAGS:
                    svg = shapes.shape_to_svg(tag, bitmap_resolver=resolver)
                    name = f"shapes/tag_{i}"
                    if tag.char_id:
                        name += f"_id{tag.char_id}"
                    name += ".svg"
                    zf.writestr(name, svg.encode("utf-8"))
                
                # Morph shapes
                elif tag.tag_type in morph.MORPH_TAG_TYPES:
                    svg = morph.morph_to_svg(tag, ratio=0.0)
                    name = f"shapes/tag_{i}_morph"
                    if tag.char_id:
                        name += f"_id{tag.char_id}"
                    name += ".svg"
                    zf.writestr(name, svg.encode("utf-8"))
                
                # Video
                elif tag.tag_type == 60:
                    info = video.parse_video_stream(tag)
                    if info:
                        name = f"video/tag_{i}_stream.json"
                        import json
                        zf.writestr(name, json.dumps(info, indent=2))
            
            except Exception:
                pass  # Skip failed exports
    
    buf.seek(0)
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{session.filename}.resources.zip"'},
    )


@router.get("/{sid}/class-hierarchy")
def class_hierarchy(sid: str):
    """Devuelve jerarquía de clases AS3 para visualización."""
    session = get_session(sid)
    classes = []
    
    for tag in session.swf.tags:
        if tag.tag_type == 82:
            _, name, abc = tag.parse_doabc() or (None, None, None)
            if not abc:
                continue
            try:
                abc.parse(tag.parse_doabc()[2])
                for i, inst in enumerate(abc.instances):
                    class_name = abc.constant_pool.multinames[inst.name] if inst.name < len(abc.constant_pool.multinames) else f"Class_{i}"
                    class_name = class_name.get("name", str(class_name)) if isinstance(class_name, dict) else str(class_name)
                    super_name = None
                    if inst.super_name:
                        super_name = abc.constant_pool.multinames[inst.super_name] if inst.super_name < len(abc.constant_pool.multinames) else str(inst.super_name)
                        super_name = super_name.get("name", str(super_name)) if isinstance(super_name, dict) else str(super_name)
                    
                    classes.append({
                        "name": class_name,
                        "super": super_name,
                        "traits": len(inst.traits),
                        "methods": sum(1 for t in inst.traits if (t.kind_flags & 0x0F) in (1, 2, 3)),
                        "fields": sum(1 for t in inst.traits if (t.kind_flags & 0x0F) in (0, 6)),
                    })
            except Exception:
                pass
    
    return {"classes": classes}


# ===== Font editing =====

FONT_TAGS = {48, 75}


class GlyphPathUpdate(BaseModel):
    glyph_idx: int
    subpaths: list  # List of subpaths with move/line/curve commands


class GlyphCodeUpdate(BaseModel):
    glyph_idx: int
    code: int


class FontPropertyUpdate(BaseModel):
    name: str | None = None
    italic: bool | None = None
    bold: bool | None = None


@router.get("/{sid}/tags/{index}/font-data")
def get_font_data(sid: str, index: int):
    session = get_session(sid)
    tag = get_tag(session, index)
    if tag.tag_type not in FONT_TAGS:
        raise HTTPException(status_code=422, detail="Not a font tag (DefineFont2/3)")
    font = text_fonts.parse_font(tag)
    if font is None:
        raise HTTPException(status_code=422, detail="Could not parse font")
    return font


@router.post("/{sid}/tags/{index}/font/update-glyph")
def update_font_glyph(sid: str, index: int, req: GlyphPathUpdate):
    session = get_session(sid)
    tag = get_tag(session, index)
    if tag.tag_type not in FONT_TAGS:
        raise HTTPException(status_code=422, detail="Not a font tag")
    font = text_fonts.parse_font(tag)
    if font is None:
        raise HTTPException(status_code=422, detail="Could not parse font")
    try:
        font_edit.update_glyph_path(font, req.glyph_idx, req.subpaths)
        new_tag = font_edit.rebuild_font_tag(font, tag.tag_type)
        session.swf.tags[index] = new_tag
        session.dirty = True
        return {"ok": True, "new_size": len(new_tag.data)}
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Glyph update failed: {exc}")


@router.post("/{sid}/tags/{index}/font/add-glyph")
def add_font_glyph(sid: str, index: int, req: GlyphPathUpdate):
    session = get_session(sid)
    tag = get_tag(session, index)
    if tag.tag_type not in FONT_TAGS:
        raise HTTPException(status_code=422, detail="Not a font tag")
    font = text_fonts.parse_font(tag)
    if font is None:
        raise HTTPException(status_code=422, detail="Could not parse font")
    try:
        # Use a default code point if not provided
        code = req.subpaths[0][0].get("code", len(font["codes"]) + 0xE000) if req.subpaths else len(font["codes"]) + 0xE000
        font_edit.add_glyph(font, req.subpaths, code)
        new_tag = font_edit.rebuild_font_tag(font, tag.tag_type)
        session.swf.tags[index] = new_tag
        session.dirty = True
        return {"ok": True, "new_size": len(new_tag.data), "glyph_idx": font["num_glyphs"] - 1}
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Add glyph failed: {exc}")


@router.post("/{sid}/tags/{index}/font/delete-glyph")
def delete_font_glyph(sid: str, index: int, glyph_idx: int):
    session = get_session(sid)
    tag = get_tag(session, index)
    if tag.tag_type not in FONT_TAGS:
        raise HTTPException(status_code=422, detail="Not a font tag")
    font = text_fonts.parse_font(tag)
    if font is None:
        raise HTTPException(status_code=422, detail="Could not parse font")
    try:
        font_edit.delete_glyph(font, glyph_idx)
        new_tag = font_edit.rebuild_font_tag(font, tag.tag_type)
        session.swf.tags[index] = new_tag
        session.dirty = True
        return {"ok": True, "new_size": len(new_tag.data)}
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Delete glyph failed: {exc}")


@router.post("/{sid}/tags/{index}/font/update-glyph-code")
def update_font_glyph_code(sid: str, index: int, req: GlyphCodeUpdate):
    session = get_session(sid)
    tag = get_tag(session, index)
    if tag.tag_type not in FONT_TAGS:
        raise HTTPException(status_code=422, detail="Not a font tag")
    font = text_fonts.parse_font(tag)
    if font is None:
        raise HTTPException(status_code=422, detail="Could not parse font")
    try:
        font_edit.update_glyph_code(font, req.glyph_idx, req.code)
        new_tag = font_edit.rebuild_font_tag(font, tag.tag_type)
        session.swf.tags[index] = new_tag
        session.dirty = True
        return {"ok": True, "new_size": len(new_tag.data)}
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Glyph code update failed: {exc}")


@router.post("/{sid}/tags/{index}/font/update-properties")
def update_font_properties(sid: str, index: int, req: FontPropertyUpdate):
    session = get_session(sid)
    tag = get_tag(session, index)
    if tag.tag_type not in FONT_TAGS:
        raise HTTPException(status_code=422, detail="Not a font tag")
    font = text_fonts.parse_font(tag)
    if font is None:
        raise HTTPException(status_code=422, detail="Could not parse font")
    try:
        font_edit.update_font_properties(font, req.name, req.italic, req.bold)
        new_tag = font_edit.rebuild_font_tag(font, tag.tag_type)
        session.swf.tags[index] = new_tag
        session.dirty = True
        return {"ok": True, "new_size": len(new_tag.data)}
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Font properties update failed: {exc}")


# ===== FLA Project Export & Sprite Sheet =====

@router.get("/{sid}/export/fla")
def export_fla(sid: str):
    """Exporta el SWF como proyecto FLA (ZIP)."""
    session = get_session(sid)
    try:
        fla_data = fla_export.export_fla_project(session.swf)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"FLA export failed: {e}")
    return Response(
        content=fla_data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{session.filename}.fla.zip"'},
    )


class SpriteSheetRequest(BaseModel):
    tag_indices: list[int] | None = None
    cols: int = 8
    padding: int = 2
    background: str | None = None


@router.post("/{sid}/export/sprite-sheet")
def export_sprite_sheet(sid: str, req: SpriteSheetRequest):
    """Genera un sprite sheet (atlas) con shapes/imágenes."""
    session = get_session(sid)
    try:
        png_bytes, meta_json = fla_export.export_sprite_sheet(
            session.swf,
            tag_indices=req.tag_indices,
            cols=req.cols,
            padding=req.padding,
            background=req.background,
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Sprite sheet export failed: {e}")
    
    if png_bytes is None:
        raise HTTPException(status_code=422, detail="No exportable shapes/images found")
    
    import base64
    return {
        "png_base64": base64.b64encode(png_bytes).decode("ascii"),
        "metadata": json.loads(meta_json),
    }


@router.get("/{sid}/export/sprite-sheet/png")
def export_sprite_sheet_png(sid: str, cols: int = 8, padding: int = 2):
    """Descarga directa del sprite sheet como PNG."""
    session = get_session(sid)
    try:
        png_bytes, _ = fla_export.export_sprite_sheet(
            session.swf, cols=cols, padding=padding
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Sprite sheet export failed: {e}")
    
    if png_bytes is None:
        raise HTTPException(status_code=422, detail="No exportable shapes/images found")
    
    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="{session.filename}.spritesheet.png"'},
    )


# ===== Robust Parsing & Validation =====

class RobustParseRequest(BaseModel):
    tolerant: bool = True
    max_tag_errors: int = 100


@router.post("/robust-parse")
async def robust_parse(file: UploadFile, tolerant: bool = True, max_tag_errors: int = 100):
    """Parsea un SWF con recuperación de errores tolerante."""
    data = await file.read()
    try:
        swf = robust_parser.read_swf_bytes_robust(data, tolerant=tolerant, max_tag_errors=max_tag_errors)
    except robust_parser.CorruptSWFError as e:
        raise HTTPException(status_code=422, detail=f"Corrupt SWF: {e}")
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Parse failed: {e}")
    
    # Convertir a respuesta similar a upload
    from .files import registry
    sid = registry.open(file.filename or "recovered.swf", b"")
    # Reemplazar el SWF en la sesión con el parseado robustamente
    session = registry.get(sid)
    session.swf = swf
    session.filename = file.filename or "recovered.swf"
    
    rect = swf.rect
    return {
        "session_id": sid,
        "filename": session.filename,
        "signature": swf.signature,
        "version": swf.version,
        "frame_rate": swf.frame_rate,
        "frame_count": swf.frame_count,
        "width": (rect["xmax"] - rect["xmin"]) / 20.0,
        "height": (rect["ymax"] - rect["ymin"]) / 20.0,
        "tag_count": len(swf.tags),
        "parse_errors": sum(1 for t in swf.tags if t.parse_error),
    }


@router.post("/validate")
async def validate_swf(file: UploadFile):
    """Valida un SWF y reporta errores/advertencias."""
    data = await file.read()
    try:
        import io
        is_valid, errors, warnings = robust_parser.validate_swf(io.BytesIO(data))
        # validate_swf espera filepath, adaptar
        # Usar read_swf_robust directamente
        swf = robust_parser.read_swf_bytes_robust(data, tolerant=True)
        errors = []
        warnings = []
        for i, tag in enumerate(swf.tags):
            if tag.parse_error:
                warnings.append(f"Tag {i} ({tag.name}): {tag.parse_error}")
        if swf.frame_count == 0:
            warnings.append("Frame count is 0")
        if swf.frame_rate <= 0:
            warnings.append(f"Invalid frame rate: {swf.frame_rate}")
        if not swf.tags or swf.tags[-1].tag_type != 0:
            warnings.append("Missing End tag")
        is_valid = len(errors) == 0
    except robust_parser.CorruptSWFError as e:
        return {"valid": False, "errors": [str(e)], "warnings": []}
    except Exception as e:
        return {"valid": False, "errors": [f"Validation error: {e}"], "warnings": []}
    
    return {"valid": is_valid, "errors": errors, "warnings": warnings}


@router.post("/repair")
async def repair_swf(file: UploadFile):
    """Intenta reparar un SWF corrupto."""
    data = await file.read()
    try:
        swf = robust_parser.read_swf_bytes_robust(data, tolerant=True)
        repaired_bytes = swf.save_bytes()
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Repair failed: {e}")
    
    return Response(
        content=repaired_bytes,
        media_type="application/x-shockwave-flash",
        headers={"Content-Disposition": f'attachment; filename="repaired_{file.filename or "file.swf"}"'},
    )
