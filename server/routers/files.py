from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from py_swf.swf_parser import collect_symbol_names
from ..sessions import registry

router = APIRouter(prefix="/api/files", tags=["files"])

TWIPS = 20.0

class FileInfo(BaseModel):
    session_id: str
    filename: str
    signature: str
    version: int
    frame_rate: float
    frame_count: int
    width: float
    height: float
    tag_count: int

class TagInfo(BaseModel):
    index: int
    code: int
    name: str
    size: int
    char_id: int | None = None
    symbol_name: str | None = None
    parse_error: str | None = None

def get_session(sid):
    try:
        return registry.get(sid)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown session id")

def file_info(sid, session):
    swf = session.swf
    rect = swf.rect
    return FileInfo(
        session_id=sid,
        filename=session.filename,
        signature=swf.signature,
        version=swf.version,
        frame_rate=swf.frame_rate,
        frame_count=swf.frame_count,
        width=(rect["xmax"] - rect["xmin"]) / TWIPS,
        height=(rect["ymax"] - rect["ymin"]) / TWIPS,
        tag_count=len(swf.tags),
    )

@router.post("", response_model=FileInfo)
async def upload_file(file: UploadFile):
    data = await file.read()
    try:
        sid = registry.open(file.filename or "untitled.swf", data)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not parse SWF: {exc}")
    return file_info(sid, registry.get(sid))

@router.get("/{sid}", response_model=FileInfo)
def get_file(sid: str):
    return file_info(sid, get_session(sid))

@router.get("/{sid}/tags", response_model=list[TagInfo])
def list_tags(sid: str):
    session = get_session(sid)
    symbol_names = collect_symbol_names(session.swf.tags)
    return [
        TagInfo(
            index=i,
            code=tag.tag_type,
            name=tag.name,
            size=len(tag.data),
            char_id=tag.char_id,
            symbol_name=symbol_names.get(tag.char_id) if tag.char_id is not None else None,
            parse_error=tag.parse_error,
        )
        for i, tag in enumerate(session.swf.tags)
    ]

def get_tag(session, index):
    tags = session.swf.tags
    if index < 0 or index >= len(tags):
        raise HTTPException(status_code=404, detail="Tag index out of range")
    return tags[index]

@router.get("/{sid}/tags/{index}/raw")
def tag_raw(sid: str, index: int, offset: int = 0, length: int | None = None):
    tag = get_tag(get_session(sid), index)
    data = tag.data[offset : offset + length if length is not None else None]
    return Response(content=data, media_type="application/octet-stream")

@router.get("/{sid}/download")
def download(sid: str):
    session = get_session(sid)
    data = session.swf.save_bytes()
    return Response(
        content=data,
        media_type="application/x-shockwave-flash",
        headers={"Content-Disposition": f'attachment; filename="{session.filename}"'},
    )

@router.delete("/{sid}")
def close_file(sid: str):
    registry.close(sid)
    return {"ok": True}
