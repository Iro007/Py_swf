"""
Editor de shapes vectoriales SWF: manipulación de vértices y edges.
Permite mover puntos, agregar/eliminar edges, cambiar estilos.
"""
from .swf_parser import BitStream, SWFTag, make_rect
from .shapes import (
    parse_shape_tag, SHAPE_TAG_TYPES, FILL_SOLID, FILL_LINEAR_GRADIENT,
    FILL_RADIAL_GRADIENT, FILL_FOCAL_RADIAL_GRADIENT,
    FILL_REPEATING_BITMAP, FILL_CLIPPED_BITMAP,
    FILL_NON_SMOOTHED_REPEATING_BITMAP, FILL_NON_SMOOTHED_CLIPPED_BITMAP,
    _read_matrix, _read_color, _read_rgba, _read_rgb, _read_style_count,
    _read_fill_style, _read_line_style_array, _read_fill_style_array,
)


def _write_rect(xmin, xmax, ymin, ymax):
    return make_rect(xmin, xmax, ymin, ymax)


def _write_rgb(stream, color):
    stream.write_bits(color["r"], 8)
    stream.write_bits(color["g"], 8)
    stream.write_bits(color["b"], 8)


def _write_rgba(stream, color):
    stream.write_bits(color["r"], 8)
    stream.write_bits(color["g"], 8)
    stream.write_bits(color["b"], 8)
    stream.write_bits(color.get("a", 255), 8)


def _write_color(stream, color, with_alpha):
    if with_alpha:
        _write_rgba(stream, color)
    else:
        _write_rgb(stream, color)


class BitWriter:
    """Escritor bit-a-bit para reconstructar tags de shape."""
    def __init__(self):
        self.data = bytearray()
        self.bit_offset = 0
    
    def write_bits(self, val, nbits):
        val = val & ((1 << nbits) - 1)
        for i in range(nbits):
            bit = (val >> (nbits - 1 - i)) & 1
            byte_idx = self.bit_offset // 8
            if byte_idx >= len(self.data):
                self.data.append(0)
            shift = 7 - (self.bit_offset % 8)
            self.data[byte_idx] |= (bit << shift)
            self.bit_offset += 1
    
    def write_signed_bits(self, val, nbits):
        if val < 0:
            val = (1 << nbits) + val
        self.write_bits(val, nbits)
    
    def align(self):
        if self.bit_offset % 8 != 0:
            self.bit_offset += 8 - (self.bit_offset % 8)
    
    def write_u16_le(self, val):
        self.align()
        self.data.extend(val.to_bytes(2, "little"))
    
    def write_u32_le(self, val):
        self.align()
        self.data.extend(val.to_bytes(4, "little"))
    
    def get_bytes(self):
        self.align()
        return bytes(self.data)


def _write_matrix(writer, m):
    has_scale = 1 if (m["scaleX"] != 1.0 or m["scaleY"] != 1.0) else 0
    writer.write_bits(has_scale, 1)
    if has_scale:
        n = 16  # fixed point 16.16
        writer.write_bits(n, 5)
        writer.write_signed_bits(int(m["scaleX"] * 65536), n)
        writer.write_signed_bits(int(m["scaleY"] * 65536), n)
    has_rotate = 1 if (m["rotateSkew0"] != 0.0 or m["rotateSkew1"] != 0.0) else 0
    writer.write_bits(has_rotate, 1)
    if has_rotate:
        n = 16
        writer.write_bits(n, 5)
        writer.write_signed_bits(int(m["rotateSkew0"] * 65536), n)
        writer.write_signed_bits(int(m["rotateSkew1"] * 65536), n)
    n = 16
    writer.write_bits(n, 5)
    writer.write_signed_bits(m["translateX"], n)
    writer.write_signed_bits(m["translateY"], n)
    writer.align()


def _write_gradient(writer, grad, with_alpha, focal=False):
    writer.write_bits(grad.get("spread", 0), 2)
    writer.write_bits(grad.get("interpolation", 0), 2)
    writer.write_bits(len(grad["stops"]), 4)
    for stop in grad["stops"]:
        writer.write_bits(stop["ratio"], 8)
        _write_color(writer, stop["color"], with_alpha)
    if focal:
        writer.write_signed_bits(int(grad.get("focalPoint", 0) * 256), 16)


def _write_fill_style(writer, style, with_alpha):
    writer.write_bits(style["type"], 8)
    if style["type"] == FILL_SOLID:
        _write_color(writer, style["color"], with_alpha)
    elif style["type"] in (FILL_LINEAR_GRADIENT, FILL_RADIAL_GRADIENT, FILL_FOCAL_RADIAL_GRADIENT):
        _write_matrix(writer, style["matrix"])
        _write_gradient(writer, style["gradient"], with_alpha, focal=(style["type"] == FILL_FOCAL_RADIAL_GRADIENT))
    elif style["type"] in (FILL_REPEATING_BITMAP, FILL_CLIPPED_BITMAP,
                           FILL_NON_SMOOTHED_REPEATING_BITMAP, FILL_NON_SMOOTHED_CLIPPED_BITMAP):
        writer.write_u16_le(style["bitmapId"])
        _write_matrix(writer, style["matrix"])


def _write_line_style(writer, style, with_alpha, use_line_style2):
    if use_line_style2:
        writer.write_u16_le(style.get("width", 20))
        writer.write_bits(style.get("startCap", 0), 2)
        writer.write_bits(style.get("joinStyle", 0), 2)
        writer.write_bits(1 if "fillStyle" in style else 0, 1)
        writer.write_bits(1 if style.get("noHScale") else 0, 1)
        writer.write_bits(1 if style.get("noVScale") else 0, 1)
        writer.write_bits(1 if style.get("pixelHinting") else 0, 1)
        writer.write_bits(0, 5)  # reserved
        writer.write_bits(1 if style.get("noClose") else 0, 1)
        writer.write_bits(style.get("endCap", 0), 2)
        if style.get("joinStyle") == 2:
            writer.write_u16_le(style.get("miterLimit", 0))
        if "fillStyle" in style:
            _write_fill_style(writer, style["fillStyle"], True)
        else:
            _write_color(writer, style["color"], True)
    else:
        writer.write_u16_le(style.get("width", 20))
        _write_color(writer, style["color"], with_alpha)


def _write_style_count(writer, count):
    if count <= 254:
        writer.write_bits(count, 8)
    else:
        writer.write_bits(0xFF, 8)
        writer.write_u16_le(count)


def _write_fill_style_array(writer, styles, with_alpha):
    _write_style_count(writer, len(styles))
    for style in styles:
        _write_fill_style(writer, style, with_alpha)


def _write_line_style_array(writer, styles, with_alpha, use_line_style2):
    _write_style_count(writer, len(styles))
    for style in styles:
        _write_line_style(writer, style, with_alpha, use_line_style2)


def _write_edges(writer, groups, num_fill_bits, num_line_bits):
    """Escribe edges desde la estructura de groups (como parse_shape_tag devuelve)."""
    fill0 = fill1 = line = 0
    cur_x = cur_y = 0
    
    for group in groups:
        # Style change record al inicio del grupo
        new_fill0 = group["fill_style0"]
        new_fill1 = group["fill_style1"]
        new_line = group["line_style"]
        
        # Emitir style change si cambió
        if (new_fill0 != fill0 or new_fill1 != fill1 or new_line != line):
            flags = 0
            if new_fill0 != fill0:
                flags |= 0x02
            if new_fill1 != fill1:
                flags |= 0x04
            if new_line != line:
                flags |= 0x08
            writer.write_bits(0, 1)  # edge flag = 0 (style change)
            writer.write_bits(flags, 5)
            if flags & 0x02:
                writer.write_bits(new_fill0, num_fill_bits)
            if flags & 0x04:
                writer.write_bits(new_fill1, num_fill_bits)
            if flags & 0x08:
                writer.write_bits(new_line, num_line_bits)
            fill0, fill1, line = new_fill0, new_fill1, new_line
        
        for subpath in group["subpaths"]:
            if not subpath:
                continue
            # Primer segmento: moveTo
            first = subpath[0]
            if first["cmd"] != "move":
                continue
            move_x = int(round(first["x"] * 20))
            move_y = int(round(first["y"] * 20))
            
            move_bits = max(1, max(move_x.bit_length(), move_y.bit_length(), 
                                   (abs(move_x - cur_x)).bit_length(), 
                                   (abs(move_y - cur_y)).bit_length()) + 1)
            move_bits = max(2, move_bits)
            
            writer.write_bits(0, 1)  # style change
            writer.write_bits(0x01, 5)  # moveTo flag
            writer.write_bits(move_bits, 5)
            writer.write_signed_bits(move_x - cur_x, move_bits)
            writer.write_signed_bits(move_y - cur_y, move_bits)
            cur_x, cur_y = move_x, move_y
            
            # Resto de segmentos
            for seg in subpath[1:]:
                if seg["cmd"] == "line":
                    x = int(round(seg["x"] * 20))
                    y = int(round(seg["y"] * 20))
                    dx = x - cur_x
                    dy = y - cur_y
                    nbits = max(2, max(dx.bit_length(), dy.bit_length(), 
                                       abs(dx).bit_length(), abs(dy).bit_length()) + 2)
                    writer.write_bits(1, 1)  # edge
                    writer.write_bits(1, 1)  # straight
                    writer.write_bits(1, 1)  # general line
                    writer.write_bits(nbits - 2, 4)
                    writer.write_signed_bits(dx, nbits)
                    writer.write_signed_bits(dy, nbits)
                    cur_x, cur_y = x, y
                elif seg["cmd"] == "curve":
                    cx = int(round(seg["cx"] * 20))
                    cy = int(round(seg["cy"] * 20))
                    x = int(round(seg["x"] * 20))
                    y = int(round(seg["y"] * 20))
                    cx_delta = cx - cur_x
                    cy_delta = cy - cur_y
                    ax_delta = x - cx
                    ay_delta = y - cy
                    nbits = max(2, max(
                        cx_delta.bit_length(), cy_delta.bit_length(),
                        ax_delta.bit_length(), ay_delta.bit_length(),
                        abs(cx_delta).bit_length(), abs(cy_delta).bit_length(),
                        abs(ax_delta).bit_length(), abs(ay_delta).bit_length()
                    ) + 2)
                    writer.write_bits(1, 1)  # edge
                    writer.write_bits(0, 1)  # curved
                    writer.write_bits(nbits - 2, 4)
                    writer.write_signed_bits(cx_delta, nbits)
                    writer.write_signed_bits(cy_delta, nbits)
                    writer.write_signed_bits(ax_delta, nbits)
                    writer.write_signed_bits(ay_delta, nbits)
                    cur_x, cur_y = x, y
    
    # EndShapeRecord
    writer.write_bits(0, 1)
    writer.write_bits(0, 5)
    writer.align()


def rebuild_shape_tag(parsed, tag_type):
    """
    Reconstruye un tag DefineShape/2/3/4 a partir de la estructura parsed.
    `parsed` es el dict que devuelve parse_shape_tag.
    """
    with_alpha = tag_type in (32, 83)
    use_line_style2 = tag_type == 83
    
    writer = BitWriter()
    
    # ShapeBounds
    bounds = parsed["bounds"]
    writer.data = bytearray(_write_rect(
        bounds["xmin"], bounds["xmax"], bounds["ymin"], bounds["ymax"]
    ))
    writer.bit_offset = len(writer.data) * 8
    
    # DefineShape4 extra: EdgeBounds + flags
    if tag_type == 83:
        # EdgeBounds (usamos los mismos bounds)
        writer.data.extend(_write_rect(
            bounds["xmin"], bounds["xmax"], bounds["ymin"], bounds["ymax"]
        ))
        writer.bit_offset = len(writer.data) * 8
        # Flags byte: reserved(5) + UsesFillWindingRule(1) + UsesNonScalingStrokes(1) + UsesScalingStrokes(1)
        writer.write_bits(0, 8)
    
    # Fill styles
    _write_fill_style_array(writer, parsed["fill_styles"], with_alpha)
    
    # Line styles
    _write_line_style_array(writer, parsed["line_styles"], with_alpha, use_line_style2)
    
    # Num fill/line bits
    num_fill = len(parsed["fill_styles"])
    num_line = len(parsed["line_styles"])
    num_fill_bits = max(1, (num_fill - 1).bit_length()) if num_fill > 0 else 0
    num_line_bits = max(1, (num_line - 1).bit_length()) if num_line > 0 else 0
    
    writer.write_bits(num_fill_bits, 4)
    writer.write_bits(num_line_bits, 4)
    
    # Edges
    _write_edges(writer, parsed["groups"], num_fill_bits, num_line_bits)
    
    # Construir tag final
    shape_id = parsed["shape_id"]
    tag_data = shape_id.to_bytes(2, "little") + writer.get_bytes()
    
    return SWFTag(tag_type, tag_data)


def update_shape_vertex(parsed, group_idx, subpath_idx, vertex_idx, new_x, new_y):
    """
    Actualiza un vértice en la estructura parsed.
    Coordenadas en pixels (se convierten a twips internamente).
    """
    group = parsed["groups"][group_idx]
    subpath = group["subpaths"][subpath_idx]
    vertex = subpath[vertex_idx]
    
    # Convertir a twips
    twip_x = int(round(new_x * 20))
    twip_y = int(round(new_y * 20))
    
    vertex["x"] = new_x
    vertex["y"] = new_y
    
    # Si es curva, también actualizar puntos de control adyacentes si es necesario
    # (simplificación: solo movemos el punto final)
    
    return parsed


def add_shape_edge(parsed, group_idx, subpath_idx, after_vertex_idx, edge_type, x, y, cx=None, cy=None):
    """
    Agrega un edge (line o curve) después de un vértice en un subpath.
    """
    group = parsed["groups"][group_idx]
    subpath = group["subpaths"][subpath_idx]
    
    new_x = x
    new_y = y
    insert_idx = after_vertex_idx + 1
    
    if edge_type == "line":
        subpath.insert(insert_idx, {"cmd": "line", "x": new_x, "y": new_y})
    elif edge_type == "curve":
        subpath.insert(insert_idx, {
            "cmd": "curve", 
            "cx": cx, "cy": cy,
            "x": new_x, "y": new_y
        })
    
    return parsed


def delete_shape_vertex(parsed, group_idx, subpath_idx, vertex_idx):
    """Elimina un vértice (edge) de un subpath."""
    group = parsed["groups"][group_idx]
    subpath = group["subpaths"][subpath_idx]
    
    if len(subpath) <= 1:
        # No se puede eliminar el único moveTo
        return parsed
    
    subpath.pop(vertex_idx)
    
    # Si el subpath queda vacío, eliminar el grupo
    if len(subpath) == 0:
        parsed["groups"].pop(group_idx)
    
    return parsed