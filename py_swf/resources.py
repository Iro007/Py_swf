import zlib
from PySide6.QtGui import QImage, QColor, QPainter
from PySide6.QtCore import QByteArray, QBuffer, QIODevice
from .swf_parser import SWFTag

def export_image(tag):
    """
    Exports the image resource in a SWFTag to standard image bytes (PNG or JPG).
    Returns (image_bytes, format_ext) or (None, None).
    """
    if tag.tag_type in (20, 36):  # DefineBitsLossless (20), DefineBitsLossless2 (36)
        if len(tag.data) < 7:
            return None, None
            
        char_id = int.from_bytes(tag.data[0:2], "little")
        fmt = tag.data[2]
        width = int.from_bytes(tag.data[3:5], "little")
        height = int.from_bytes(tag.data[5:7], "little")
        
        is_lossless2 = (tag.tag_type == 36)
        
        compressed_data = tag.data[7:]
        try:
            raw_data = zlib.decompress(compressed_data)
        except Exception:
            return None, None
            
        if fmt == 5:  # 24-bit RGB (Lossless) or 32-bit ARGB (Lossless2)
            # The SWF format stores pixels as [A, R, G, B] in big-endian bytes
            out_pixels = bytearray(width * height * 4)
            for i in range(width * height):
                a = raw_data[i*4]
                r = raw_data[i*4+1]
                g = raw_data[i*4+2]
                b = raw_data[i*4+3]
                
                if is_lossless2 and a > 0 and a < 255:
                    # Un-premultiply color channels for standard PNG
                    r = min(255, int(r * 255 / a))
                    g = min(255, int(g * 255 / a))
                    b = min(255, int(b * 255 / a))
                elif not is_lossless2:
                    a = 255  # Lossless 1 has no alpha, but stored as 0x00, R, G, B
                    
                # QImage.Format_RGBA8888 expects R, G, B, A order in bytes
                out_pixels[i*4] = r
                out_pixels[i*4+1] = g
                out_pixels[i*4+2] = b
                out_pixels[i*4+3] = a
                
            img = QImage(out_pixels, width, height, QImage.Format_RGBA8888)
            ba = QByteArray()
            buf = QBuffer(ba)
            buf.open(QBuffer.WriteOnly)
            img.save(buf, "PNG")
            return bytes(ba), "png"
            
        elif fmt == 3:  # 8-bit colormapped index image
            if len(raw_data) < 1:
                return None, None
            colormap_count = tag.data[7] + 1 if len(tag.data) > 7 else 0  # wait, count is at start of zlib decompressed stream?
            # Actually, colormap_count is stored as UI8 at start of zlib stream in SWF!
            # Let's verify: Yes! First byte of decompressed zlib is colormap_count.
            colormap_count = raw_data[0] + 1
            # Color table starts at index 1.
            # Lossless (tag 20) color table has RGB (3 bytes per color).
            # Lossless2 (tag 36) color table has RGBA (4 bytes per color).
            color_size = 4 if is_lossless2 else 3
            table_end = 1 + colormap_count * color_size
            color_table = raw_data[1:table_end]
            pixel_indices = raw_data[table_end:]
            
            # Reconstruct image
            out_pixels = bytearray(width * height * 4)
            # Row size in indices is width bytes, padded to 32-bit (4-byte) boundary!
            row_padded_size = (width + 3) & ~3
            
            for y in range(height):
                for x in range(width):
                    idx_in_data = y * row_padded_size + x
                    if idx_in_data >= len(pixel_indices):
                        break
                    color_idx = pixel_indices[idx_in_data]
                    
                    if color_idx < colormap_count:
                        if is_lossless2:
                            a = color_table[color_idx*4]
                            r = color_table[color_idx*4+1]
                            g = color_table[color_idx*4+2]
                            b = color_table[color_idx*4+3]
                            if a > 0 and a < 255:
                                r = min(255, int(r * 255 / a))
                                g = min(255, int(g * 255 / a))
                                b = min(255, int(b * 255 / a))
                        else:
                            r = color_table[color_idx*3]
                            g = color_table[color_idx*3+1]
                            b = color_table[color_idx*3+2]
                            a = 255
                    else:
                        r, g, b, a = 0, 0, 0, 0
                        
                    pixel_idx = (y * width + x) * 4
                    out_pixels[pixel_idx] = r
                    out_pixels[pixel_idx+1] = g
                    out_pixels[pixel_idx+2] = b
                    out_pixels[pixel_idx+3] = a
                    
            img = QImage(out_pixels, width, height, QImage.Format_RGBA8888)
            ba = QByteArray()
            buf = QBuffer(ba)
            buf.open(QBuffer.WriteOnly)
            img.save(buf, "PNG")
            return bytes(ba), "png"
            
    elif tag.tag_type == 21:  # DefineBitsJPEG2
        if len(tag.data) < 2:
            return None, None
        return tag.data[2:], "jpg"
        
    elif tag.tag_type == 35:  # DefineBitsJPEG3 (JPEG with alpha)
        if len(tag.data) < 6:
            return None, None
        char_id = int.from_bytes(tag.data[0:2], "little")
        alpha_offset = int.from_bytes(tag.data[2:6], "little")
        jpeg_bytes = tag.data[6 : 6 + alpha_offset]
        alpha_compressed = tag.data[6 + alpha_offset :]
        
        try:
            alpha_bytes = zlib.decompress(alpha_compressed)
        except Exception:
            # Fallback to exporting just JPEG if alpha decompression fails
            return jpeg_bytes, "jpg"
            
        img = QImage()
        if not img.loadFromData(jpeg_bytes, "JPG"):
            return None, None
            
        img = img.convertToFormat(QImage.Format_RGBA8888)
        width = img.width()
        height = img.height()
        
        # Combine alpha channel
        bits = img.bits()
        # QImage bits is a memoryview of RGBA
        for i in range(width * height):
            if i < len(alpha_bytes):
                bits[i*4 + 3] = alpha_bytes[i]
                
        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QBuffer.WriteOnly)
        img.save(buf, "PNG")
        return bytes(ba), "png"
        
    return None, None

def replace_image(tag, new_image_bytes, extension):
    """
    Replaces the image in a tag with a new image.
    Returns a new SWFTag object.
    """
    char_id = int.from_bytes(tag.data[0:2], "little")
    
    if tag.tag_type in (20, 36):
        is_lossless2 = (tag.tag_type == 36)
        
        img = QImage()
        if not img.loadFromData(new_image_bytes):
            raise ValueError("Failed to load image data")
            
        img = img.convertToFormat(QImage.Format_RGBA8888)
        width = img.width()
        height = img.height()
        
        bits = img.constBits()
        raw_pixels = bytearray(width * height * 4)
        
        for i in range(width * height):
            r = bits[i*4]
            g = bits[i*4+1]
            b = bits[i*4+2]
            a = bits[i*4+3]
            
            if is_lossless2:
                # Premultiply alpha channels
                r = int(r * a / 255)
                g = int(g * a / 255)
                b = int(b * a / 255)
            else:
                a = 255  # Lossless 1 expects opaque
                
            # SWF stores ARGB format [A, R, G, B]
            raw_pixels[i*4] = a
            raw_pixels[i*4+1] = r
            raw_pixels[i*4+2] = g
            raw_pixels[i*4+3] = b
            
        compressed = zlib.compress(bytes(raw_pixels))
        
        # Build tag payload:
        # character_id (UI16) + format (UI8) + width (UI16) + height (UI16) + compressed pixels
        tag_data = bytearray()
        tag_data.extend(char_id.to_bytes(2, "little"))
        tag_data.append(5)  # format 5 (ARGB)
        tag_data.extend(width.to_bytes(2, "little"))
        tag_data.extend(height.to_bytes(2, "little"))
        tag_data.extend(compressed)
        
        return SWFTag(tag.tag_type, bytes(tag_data))
        
    elif tag.tag_type == 21:
        # Replace JPG data directly
        tag_data = bytearray()
        tag_data.extend(char_id.to_bytes(2, "little"))
        tag_data.extend(new_image_bytes)
        return SWFTag(21, bytes(tag_data))
        
    elif tag.tag_type == 35:
        # DefineBitsJPEG3
        img = QImage()
        if not img.loadFromData(new_image_bytes):
            raise ValueError("Failed to load image data")
            
        img = img.convertToFormat(QImage.Format_RGBA8888)
        width = img.width()
        height = img.height()
        
        # 1. Extract alpha channel
        bits = img.constBits()
        alpha_bytes = bytearray(width * height)
        for i in range(width * height):
            alpha_bytes[i] = bits[i*4 + 3]
        alpha_compressed = zlib.compress(alpha_bytes)
        
        # 2. Paint opaque background for JPEG extraction
        opaque_img = QImage(width, height, QImage.Format_RGB32)
        opaque_img.fill(QColor("white"))
        painter = QPainter(opaque_img)
        painter.drawImage(0, 0, img)
        painter.end()
        
        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QBuffer.WriteOnly)
        opaque_img.save(buf, "JPG", 90)
        jpeg_bytes = bytes(ba)
        
        # Build tag payload:
        # character_id (UI16) + alpha_data_offset (UI32) + jpeg_data + alpha_data
        tag_data = bytearray()
        tag_data.extend(char_id.to_bytes(2, "little"))
        tag_data.extend(len(jpeg_bytes).to_bytes(4, "little"))
        tag_data.extend(jpeg_bytes)
        tag_data.extend(alpha_compressed)
        
        return SWFTag(35, bytes(tag_data))
        
    return tag
