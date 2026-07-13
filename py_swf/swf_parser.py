import zlib
import lzma
import struct

TAG_NAMES = {
    0: "End",
    1: "ShowFrame",
    2: "DefineShape",
    4: "PlaceObject",
    5: "RemoveObject",
    6: "DefineBits",
    7: "DefineButton",
    8: "JPEGTables",
    9: "SetBackgroundColor",
    10: "DefineFont",
    11: "DefineText",
    12: "DoAction",
    13: "DefineFontInfo",
    14: "DefineSound",
    15: "StartSound",
    17: "DefineButtonSound",
    18: "SoundStreamHead",
    19: "SoundStreamBlock",
    20: "DefineBitsLossless",
    21: "DefineBitsJPEG2",
    22: "DefineShape2",
    23: "DefineButtonCxform",
    24: "Protect",
    26: "PlaceObject2",
    28: "RemoveObject2",
    32: "DefineShape3",
    33: "DefineText2",
    34: "DefineButton2",
    35: "DefineBitsJPEG3",
    36: "DefineBitsLossless2",
    37: "DefineEditText",
    39: "DefineSprite",
    43: "FrameLabel",
    45: "SoundStreamHead2",
    46: "DefineMorphShape",
    48: "DefineFont2",
    56: "ExportAssets",
    57: "ImportAssets",
    58: "EnableDebugger",
    59: "DoInitAction",
    60: "DefineVideoStream",
    61: "VideoFrame",
    62: "DefineFontInfo2",
    64: "EnableDebugger2",
    65: "ScriptLimits",
    66: "SetTabIndex",
    69: "FileAttributes",
    70: "PlaceObject3",
    71: "ImportAssets2",
    73: "DefineFontAlignZones",
    72: "FileAttributes",
    73: "DefineFontAlignZones",
    74: "CSMTextSettings",
    75: "DefineFont3",
    76: "SymbolClass",
    77: "Metadata",
    78: "DefineScalingGrid",
    82: "DoABC",
    83: "DefineShape4",
    84: "DefineMorphShape2",
    86: "DefineSceneAndFrameLabelData",
    87: "DefineBinaryData",
    88: "DefineFontName",
    89: "StartSound2",
    90: "DefineBitsJPEG4",
    91: "DefineFont4",
}

class BitStream:
    def __init__(self, data):
        self.data = data
        self.byte_offset = 0
        self.bit_offset = 0
        
    def read_bits(self, nbits):
        if nbits == 0:
            return 0
        val = 0
        bits_needed = nbits
        while bits_needed > 0:
            if self.byte_offset >= len(self.data):
                raise EOFError("BitStream EOF")
            current_byte = self.data[self.byte_offset]
            bits_available = 8 - self.bit_offset
            bits_to_read = min(bits_needed, bits_available)
            shift = bits_available - bits_to_read
            mask = (1 << bits_to_read) - 1
            chunk = (current_byte >> shift) & mask
            val = (val << bits_to_read) | chunk
            
            self.bit_offset += bits_to_read
            if self.bit_offset == 8:
                self.bit_offset = 0
                self.byte_offset += 1
            bits_needed -= bits_to_read
        return val

    def read_signed_bits(self, nbits):
        val = self.read_bits(nbits)
        if nbits > 0 and (val & (1 << (nbits - 1))):
            val -= (1 << nbits)
        return val
        
    def align(self):
        if self.bit_offset > 0:
            self.bit_offset = 0
            self.byte_offset += 1

def parse_rect(stream):
    nbits = stream.read_bits(5)
    xmin = stream.read_signed_bits(nbits)
    xmax = stream.read_signed_bits(nbits)
    ymin = stream.read_signed_bits(nbits)
    ymax = stream.read_signed_bits(nbits)
    stream.align()
    return {"xmin": xmin, "xmax": xmax, "ymin": ymin, "ymax": ymax}

def make_rect(xmin, xmax, ymin, ymax):
    # Find the max bits needed to represent any of these coords (signed)
    max_val = max(abs(xmin), abs(xmax), abs(ymin), abs(ymax))
    nbits = 0
    # Calculate bits needed for the value (excluding sign bit)
    while (1 << nbits) <= max_val:
        nbits += 1
    # Plus sign bit
    nbits += 1
    # Minimum bit size is 1 bit (if all are 0)
    nbits = max(1, nbits)
    
    # We pack: nbits (5 bits) + 4 coordinates * nbits
    total_bits = 5 + 4 * nbits
    total_bytes = (total_bits + 7) // 8
    data = bytearray(total_bytes)
    
    bit_offset = 0
    def write_bits(val, num_bits):
        nonlocal bit_offset
        val = val & ((1 << num_bits) - 1)
        for i in range(num_bits):
            bit_idx = num_bits - 1 - i
            bit = (val >> bit_idx) & 1
            byte_idx = bit_offset // 8
            shift = 7 - (bit_offset % 8)
            data[byte_idx] |= (bit << shift)
            bit_offset += 1
            
    write_bits(nbits, 5)
    write_bits(xmin, nbits)
    write_bits(xmax, nbits)
    write_bits(ymin, nbits)
    write_bits(ymax, nbits)
    return bytes(data)

class SWFTag:
    def __init__(self, tag_type, data):
        self.tag_type = tag_type
        self.data = data
        
    @property
    def name(self):
        return TAG_NAMES.get(self.tag_type, f"Unknown_{self.tag_type}")
        
    @property
    def is_doabc(self):
        return self.tag_type == 82
        
    def parse_doabc(self):
        if not self.is_doabc or len(self.data) < 4:
            return None
        flags = int.from_bytes(self.data[0:4], "little")
        name = ""
        abc_bytes = b""
        if len(self.data) > 4:
            name_end = self.data.find(b"\x00", 4)
            if name_end == -1:
                name = self.data[4:].decode("utf-8", errors="replace")
                abc_bytes = self.data[4:]
            else:
                name = self.data[4:name_end].decode("utf-8", errors="replace")
                abc_bytes = self.data[name_end + 1:]
        return flags, name, abc_bytes
        
    def pack(self):
        tag_len = len(self.data)
        if tag_len < 63:
            header = (self.tag_type << 6) | tag_len
            return header.to_bytes(2, "little") + self.data
        else:
            header = (self.tag_type << 6) | 0x3F
            return header.to_bytes(2, "little") + tag_len.to_bytes(4, "little") + self.data

    def __repr__(self):
        return f"<SWFTag {self.name} ({self.tag_type}), size={len(self.data)}>"

class SWFFile:
    def __init__(self):
        self.signature = "FWS"
        self.version = 15
        self.rect = {"xmin": 0, "xmax": 11000, "ymin": 0, "ymax": 8250}
        self.frame_rate = 12.0
        self.frame_count = 1
        self.tags = []

    def read_file(self, filepath):
        with open(filepath, "rb") as f:
            header_bytes = f.read(8)
            if len(header_bytes) < 8:
                raise ValueError("Invalid SWF file: header too short")
                
            self.signature = header_bytes[0:3].decode("ascii", errors="ignore")
            if self.signature not in ("FWS", "CWS", "ZWS"):
                raise ValueError(f"Unknown SWF signature: {self.signature}")
                
            self.version = header_bytes[3]
            decompressed_length = int.from_bytes(header_bytes[4:8], "little")
            
            # Read rest of file
            rest_data = f.read()
            
            if self.signature == "CWS":
                decompressed_data = zlib.decompress(rest_data)
            elif self.signature == "ZWS":
                # LZMA compressed:
                # 4 bytes signature + 1 byte version + 4 bytes decompressed length
                # followed by 4 bytes compressed length, then 5 bytes lzma properties, then lzma data
                # Python's lzma module expects properties at the start of stream or formatted as XZ
                # The format in SWF is LZMA ALONE (with properties first but compressed length omitted)
                # Actually, in ZWS, the compressed length is stored as 4 bytes (UI32) at the start of compression stream,
                # then 5 bytes of LZMA properties (dicsize, etc.), then the LZMA raw stream.
                compressed_len = int.from_bytes(rest_data[0:4], "little")
                lzma_properties = rest_data[4:9]
                lzma_data = rest_data[9:]
                # Reconstruct standard LZMA header: properties + 8 bytes uncompressed size + payload
                uncompressed_size_bytes = decompressed_length.to_bytes(8, "little")
                lzma_stream = lzma_properties + uncompressed_size_bytes + lzma_data
                decompressed_data = lzma.decompress(lzma_stream)
            else:
                decompressed_data = rest_data
                
            # Verify decompressed length (header length includes 8 bytes header)
            # The decompressed data length should match decompressed_length - 8
            # (though sometimes minor size mismatches occur in wild, we won't throw)
            
            self._parse_decompressed(decompressed_data)

    def _parse_decompressed(self, data):
        stream = BitStream(data)
        self.rect = parse_rect(stream)
        
        # Read FrameRate
        # Minor byte (fraction), Major byte (integer)
        # We read 2 bytes from stream
        fps_bytes = data[stream.byte_offset : stream.byte_offset + 2]
        stream.byte_offset += 2
        
        fraction = fps_bytes[0]
        integer = fps_bytes[1]
        self.frame_rate = integer + fraction / 256.0
        
        # Read FrameCount (UI16)
        self.frame_count = int.from_bytes(data[stream.byte_offset : stream.byte_offset + 2], "little")
        stream.byte_offset += 2
        
        # Parse tags
        self.tags = []
        offset = stream.byte_offset
        while offset < len(data):
            if offset + 2 > len(data):
                break
            header = int.from_bytes(data[offset : offset + 2], "little")
            tag_type = header >> 6
            tag_len = header & 0x3F
            length_bytes = 2
            if tag_len == 0x3F:
                if offset + 6 > len(data):
                    break
                tag_len = int.from_bytes(data[offset + 2 : offset + 6], "little")
                length_bytes = 6
                
            offset += length_bytes
            tag_data = data[offset : offset + tag_len]
            offset += tag_len
            
            tag = SWFTag(tag_type, tag_data)
            self.tags.append(tag)
            
            if tag_type == 0:  # End Tag
                break

    def save_file(self, filepath):
        # 1. Rebuild decompressed body
        body = bytearray()
        rect_bytes = make_rect(self.rect["xmin"], self.rect["xmax"], self.rect["ymin"], self.rect["ymax"])
        body.extend(rect_bytes)
        
        # FrameRate: minor byte (fraction), major byte (integer)
        integer = int(self.frame_rate)
        fraction = int((self.frame_rate - integer) * 256) & 0xFF
        body.append(fraction)
        body.append(integer)
        
        # FrameCount
        body.extend(self.frame_count.to_bytes(2, "little"))
        
        # Pack all tags
        # Ensure there is an End tag at the end
        if not self.tags or self.tags[-1].tag_type != 0:
            self.tags.append(SWFTag(0, b""))
            
        for tag in self.tags:
            body.extend(tag.pack())
            
        # Total decompressed file size = body size + 8 bytes header
        decompressed_size = len(body) + 8
        
        header = bytearray()
        header.extend(self.signature.encode("ascii"))
        header.append(self.version)
        header.extend(decompressed_size.to_bytes(4, "little"))
        
        if self.signature == "CWS":
            compressed_body = zlib.compress(body)
        elif self.signature == "ZWS":
            # LZMA compression:
            # We compress the body using lzma, then extract properties.
            # Python's lzma.compress yields a stream with properties + uncompressed size (8 bytes) + payload
            # We need to construct: 4 bytes compressed len, 5 bytes properties, then payload
            raw_lzma = lzma.compress(body, format=lzma.FORMAT_ALONE)
            properties = raw_lzma[0:5]
            # uncompressed size raw_lzma[5:13] is omitted in SWF
            payload = raw_lzma[13:]
            compressed_len = len(payload)
            compressed_body = bytearray()
            compressed_body.extend(compressed_len.to_bytes(4, "little"))
            compressed_body.extend(properties)
            compressed_body.extend(payload)
        else:
            compressed_body = body
            
        with open(filepath, "wb") as f:
            f.write(header)
            f.write(compressed_body)
