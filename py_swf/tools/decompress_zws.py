"""Attempt to decompress a ZWS (LZMA-compressed SWF) buffer.
Usage: python py_swf/tools/decompress_zws.py <input_file> > uncompressed.swf
Or: pass base64 on stdin and it prints raw bytes to stdout.
Note: This is a best-effort helper and may not support all LZMA-wrapped SWFs.
"""
import sys
from pathlib import Path
import lzma
import base64


def decompress_zws_bytes(data: bytes) -> bytes:
    # SWF ZWS layout (best-effort): header 3 bytes 'ZWS', version 1 byte, fileLength 4 bytes (LE)
    # The compressed payload typically starts at offset 12 (after a 8-byte header plus 4 bytes of LZMA properties/size in some variants)
    # Try common variants: compressed from offset 8 or 12.
    if len(data) < 12:
        raise ValueError('Data too short for ZWS')
    # Try decompress from offset 8
    for start in (8, 12):
        try:
            comp = data[start:]
            # lzma.decompress expects a full LZMA stream (xz headers) — try raw lzma with preset format
            # Use LZMADecompressor for raw stream attempts
            dec = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
            body = dec.decompress(comp)
            # Reconstruct full SWF: 'FWS' + version + fileLength + body
            header = bytearray(data[:8])
            header[0:3] = b'FWS'
            # fileLength (bytes 4..7) should be updated to len(header)+len(body)
            total_len = 8 + len(body)
            header[4:8] = total_len.to_bytes(4, 'little')
            return bytes(header) + body
        except Exception:
            continue
    # If all failed, try lzma with default auto-detection
    try:
        body = lzma.decompress(data[12:])
        header = bytearray(data[:8])
        header[0:3] = b'FWS'
        total_len = 8 + len(body)
        header[4:8] = total_len.to_bytes(4, 'little')
        return bytes(header) + body
    except Exception as e:
        raise


def main():
    if len(sys.argv) >= 2:
        p = Path(sys.argv[1])
        data = p.read_bytes()
    else:
        data = sys.stdin.buffer.read()
        # If data looks like base64 text, decode
        if b' ' not in data and b'\n' in data[:80]:
            try:
                data = base64.b64decode(data)
            except Exception:
                pass
    if not data.startswith(b'ZWS'):
        sys.stderr.write('Not a ZWS file\n')
        sys.exit(2)
    try:
        out = decompress_zws_bytes(data)
        sys.stdout.buffer.write(out)
    except Exception as e:
        sys.stderr.write('Decompression failed: %s\n' % (e,))
        sys.exit(3)

if __name__ == '__main__':
    main()
