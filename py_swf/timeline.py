"""
Modelo de display list / timeline SWF y render de frames a SVG.

Procesa PlaceObject (4), PlaceObject2 (26), PlaceObject3 (70), RemoveObject
(5/28) y ShowFrame (1) para la timeline principal y para cada DefineSprite
(39), y compone el frame N transformando los characters (shapes, morphs,
textos, sprites anidados) con sus MATRIX.

Aproximaciones v1 (marcadas en la UI): sin color transforms, clipping,
filtros ni blend modes.
"""
from .swf_parser import BitStream, SWFTag
from . import shapes, morph, text_fonts

PLACE_TAGS = (4, 26, 70)
REMOVE_TAGS = (5, 28)
SHOW_FRAME = 1

RENDERABLE_TAGS = shapes.SHAPE_TAG_TYPES + morph.MORPH_TAG_TYPES + text_fonts.TEXT_TAGS[:2] + (39,)


def _read_cxform(stream, with_alpha):
    """CXFORM/CXFORMWITHALPHA: solo lo consumimos para avanzar el stream."""
    has_add = stream.read_bits(1)
    has_mult = stream.read_bits(1)
    nbits = stream.read_bits(4)
    channels = 4 if with_alpha else 3
    if has_mult:
        for _ in range(channels):
            stream.read_signed_bits(nbits)
    if has_add:
        for _ in range(channels):
            stream.read_signed_bits(nbits)
    stream.align()


def _read_matrix_dict(stream):
    from .shapes import _read_matrix

    return _read_matrix(stream)


IDENTITY = {"scaleX": 1.0, "scaleY": 1.0, "rotateSkew0": 0.0, "rotateSkew1": 0.0,
            "translateX": 0, "translateY": 0}


def parse_place_tag(tag):
    """Devuelve dict {depth, char_id?, matrix?, ratio?, move} o None."""
    data = tag.data
    if tag.tag_type == 4:
        if len(data) < 4:
            return None
        char_id = int.from_bytes(data[0:2], "little")
        depth = int.from_bytes(data[2:4], "little")
        stream = BitStream(data[4:])
        matrix = _read_matrix_dict(stream)
        return {"depth": depth, "char_id": char_id, "matrix": matrix, "ratio": 0, "move": False}

    if tag.tag_type in (26, 70):
        stream = BitStream(data)
        flags = stream.read_bits(8)
        has_clip_actions = bool(flags & 0x80)
        has_clip_depth = bool(flags & 0x40)
        has_name = bool(flags & 0x20)
        has_ratio = bool(flags & 0x10)
        has_cxform = bool(flags & 0x08)
        has_matrix = bool(flags & 0x04)
        has_char = bool(flags & 0x02)
        move = bool(flags & 0x01)

        has_class_name = has_image = has_filters = has_blend = False
        if tag.tag_type == 70:
            flags2 = stream.read_bits(8)
            has_image = bool(flags2 & 0x10)
            has_class_name = bool(flags2 & 0x08) or (has_image and has_char)
            has_filters = bool(flags2 & 0x01)
            has_blend = bool(flags2 & 0x02)
            # bits: reserved(1) opaqueBg(1) visible(1) hasImage hasClassName cacheAsBitmap hasBlend hasFilters
            # (leemos con máscaras conservadoras; los campos extra se ignoran)

        depth = stream.read_u16_le()
        result = {"depth": depth, "move": move}
        if has_class_name:
            # cstring
            while True:
                c = stream.read_bits(8)
                if c == 0:
                    break
        if has_char:
            result["char_id"] = stream.read_u16_le()
        if has_matrix:
            result["matrix"] = _read_matrix_dict(stream)
        if has_cxform:
            _read_cxform(stream, with_alpha=True)
        if has_ratio:
            result["ratio"] = stream.read_u16_le()
        # name/clipdepth/filters/blend/clipactions: no los necesitamos para render v1
        return result
    return None


def build_timeline(tags):
    """
    Recorre los tags acumulando el estado de la display list por frame.
    Devuelve lista de frames; cada frame es dict {depth: {char_id, matrix, ratio}}.
    """
    frames = []
    display = {}
    for tag in tags:
        if tag.tag_type in PLACE_TAGS:
            place = parse_place_tag(tag)
            if not place:
                continue
            depth = place["depth"]
            prev = display.get(depth, {})
            entry = {
                "char_id": place.get("char_id", prev.get("char_id")),
                "matrix": place.get("matrix", prev.get("matrix", IDENTITY)),
                "ratio": place.get("ratio", prev.get("ratio", 0)),
            }
            if entry["char_id"] is not None:
                display[depth] = entry
        elif tag.tag_type in REMOVE_TAGS:
            data = tag.data
            off = 2 if tag.tag_type == 5 else 0
            if len(data) >= off + 2:
                depth = int.from_bytes(data[off : off + 2], "little")
                display.pop(depth, None)
        elif tag.tag_type == SHOW_FRAME:
            frames.append({d: dict(e) for d, e in display.items()})
    if not frames and display:
        frames.append({d: dict(e) for d, e in display.items()})
    return frames


def parse_sprite(tag):
    """DefineSprite (39): devuelve (char_id, frame_count, tags_anidados)."""
    if tag.tag_type != 39 or len(tag.data) < 4:
        return None
    char_id = int.from_bytes(tag.data[0:2], "little")
    frame_count = int.from_bytes(tag.data[2:4], "little")
    inner = []
    data = tag.data
    offset = 4
    while offset + 2 <= len(data):
        header = int.from_bytes(data[offset : offset + 2], "little")
        tag_type = header >> 6
        tag_len = header & 0x3F
        offset += 2
        if tag_len == 0x3F:
            if offset + 4 > len(data):
                break
            tag_len = int.from_bytes(data[offset : offset + 4], "little")
            offset += 4
        inner.append(SWFTag(tag_type, data[offset : offset + tag_len]))
        offset += tag_len
        if tag_type == 0:
            break
    return char_id, frame_count, inner


def _place_transform(m):
    """MATRIX de colocación → transform SVG (translate en twips → px)."""
    return (
        f"matrix({m['scaleX']:.6f} {m['rotateSkew0']:.6f} {m['rotateSkew1']:.6f} "
        f"{m['scaleY']:.6f} {m['translateX'] / 20.0:.3f} {m['translateY'] / 20.0:.3f})"
    )


class FrameRenderer:
    """Renderiza frames componiendo characters por id sobre la display list."""

    def __init__(self, tags, bitmap_resolver=None):
        self.tags = tags
        self.bitmap_resolver = bitmap_resolver
        self.by_id = {t.char_id: t for t in tags if t.char_id is not None}
        self.fonts = text_fonts.collect_fonts(tags)
        self._defs = []
        self._uid = 0

    def _next_prefix(self):
        self._uid += 1
        return f"c{self._uid}"

    def render_character(self, char_id, ratio=0, depth_budget=8):
        tag = self.by_id.get(char_id)
        if tag is None or depth_budget <= 0:
            return ""
        if tag.tag_type in shapes.SHAPE_TAG_TYPES:
            defs, body, bounds = shapes.shape_to_svg_fragment(
                tag, id_prefix=self._next_prefix(), bitmap_resolver=self.bitmap_resolver
            )
            self._defs.append(defs)
            return body
        if tag.tag_type in morph.MORPH_TAG_TYPES:
            defs, body, _ = morph.morph_to_svg_fragment(
                tag, ratio / 65535.0, id_prefix=self._next_prefix()
            )
            self._defs.append(defs)
            return body
        if tag.tag_type in text_fonts.TEXT_TAGS:
            text = text_fonts.parse_text_tag(tag)
            if text:
                body, _ = text_fonts.text_to_svg_fragment(text, self.fonts)
                return body
            return ""
        if tag.tag_type == 39:
            parsed = parse_sprite(tag)
            if not parsed:
                return ""
            _, _, inner = parsed
            frames = build_timeline(inner)
            if not frames:
                return ""
            return self.render_display(frames[0], depth_budget - 1)
        return ""

    def render_display(self, display, depth_budget=8):
        parts = []
        for depth in sorted(display):
            entry = display[depth]
            body = self.render_character(entry["char_id"], entry.get("ratio", 0), depth_budget)
            if body:
                parts.append(f"<g transform='{_place_transform(entry['matrix'])}'>{body}</g>")
        return "".join(parts)

    def render_frame_svg(self, display, stage_rect, background=None):
        self._defs = []
        body = self.render_display(display)
        width = max(1, round((stage_rect["xmax"] - stage_rect["xmin"]) / 20.0))
        height = max(1, round((stage_rect["ymax"] - stage_rect["ymin"]) / 20.0))
        ox, oy = stage_rect["xmin"] / 20.0, stage_rect["ymin"] / 20.0
        parts = [
            f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='{ox:.2f} {oy:.2f} {width} {height}' "
            f"width='{width}' height='{height}'>"
        ]
        if background:
            parts.append(
                f"<rect x='{ox:.2f}' y='{oy:.2f}' width='{width}' height='{height}' fill='{background}'/>"
            )
        defs = "".join(d for d in self._defs if d)
        if defs:
            parts.append(f"<defs>{defs}</defs>")
        parts.append(body)
        parts.append("</svg>")
        return "".join(parts)


def get_background_color(tags):
    for tag in tags:
        if tag.tag_type == 9 and len(tag.data) >= 3:
            r, g, b = tag.data[0], tag.data[1], tag.data[2]
            return f"rgb({r},{g},{b})"
    return None


def render_frame(swf, frame_index, bitmap_resolver=None):
    """Renderiza el frame N (0-based) de la timeline principal como SVG."""
    frames = build_timeline(swf.tags)
    if not frames:
        return None, 0
    frame_index = max(0, min(frame_index, len(frames) - 1))
    renderer = FrameRenderer(swf.tags, bitmap_resolver=bitmap_resolver)
    svg = renderer.render_frame_svg(
        frames[frame_index], swf.rect, background=get_background_color(swf.tags)
    )
    return svg, len(frames)


def render_sprite_frame(swf, sprite_tag, frame_index, bitmap_resolver=None):
    """Renderiza el frame N de un DefineSprite como SVG (bounds = stage)."""
    parsed = parse_sprite(sprite_tag)
    if not parsed:
        return None, 0
    _, _, inner = parsed
    frames = build_timeline(inner)
    if not frames:
        return None, 0
    frame_index = max(0, min(frame_index, len(frames) - 1))
    renderer = FrameRenderer(swf.tags, bitmap_resolver=bitmap_resolver)
    svg = renderer.render_frame_svg(frames[frame_index], swf.rect)
    return svg, len(frames)
