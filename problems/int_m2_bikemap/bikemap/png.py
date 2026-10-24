"""Just enough PNG to write 8-bit RGB images and read them back (no third-party deps)."""
from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass, field

SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _chunk(kind: bytes, payload: bytes) -> bytes:
    crc = zlib.crc32(kind + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", crc)


def encode_png(width: int, height: int, rgb: bytes, text: dict[str, str] | None = None) -> bytes:
    """Encode raw RGB bytes (row-major, 3 bytes per pixel) as a PNG file."""
    if len(rgb) != width * height * 3:
        raise ValueError("pixel buffer size does not match width*height*3")
    stride = width * 3
    raw = b"".join(b"\x00" + rgb[y * stride:(y + 1) * stride] for y in range(height))
    out = [SIGNATURE, _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))]
    for key, value in (text or {}).items():
        out.append(_chunk(b"tEXt", key.encode("latin-1") + b"\x00" + value.encode("latin-1")))
    out.append(_chunk(b"IDAT", zlib.compress(raw, 6)))
    out.append(_chunk(b"IEND", b""))
    return b"".join(out)


def read_chunks(data: bytes) -> list[tuple[bytes, bytes]]:
    """Split a PNG into (type, payload) pairs, checking signature and CRCs."""
    if not data.startswith(SIGNATURE):
        raise ValueError("not a PNG file")
    chunks, pos = [], len(SIGNATURE)
    while pos < len(data):
        if pos + 8 > len(data):
            raise ValueError("truncated chunk header")
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        kind = data[pos + 4:pos + 8]
        payload = data[pos + 8:pos + 8 + length]
        (crc,) = struct.unpack(">I", data[pos + 8 + length:pos + 12 + length])
        if len(payload) != length or zlib.crc32(kind + payload) & 0xFFFFFFFF != crc:
            raise ValueError(f"bad {kind!r} chunk")
        chunks.append((kind, payload))
        pos += 12 + length
        if kind == b"IEND":
            break
    return chunks


@dataclass
class PngInfo:
    width: int
    height: int
    text: dict[str, str] = field(default_factory=dict)


def png_info(data: bytes) -> PngInfo:
    chunks = read_chunks(data)
    if not chunks or chunks[0][0] != b"IHDR":
        raise ValueError("missing IHDR")
    width, height = struct.unpack(">II", chunks[0][1][:8])
    text = {}
    for kind, payload in chunks:
        if kind == b"tEXt":
            key, _, value = payload.partition(b"\x00")
            text[key.decode("latin-1")] = value.decode("latin-1")
    return PngInfo(width, height, text)


def decode_rgb(data: bytes) -> tuple[int, int, bytes]:
    """Decode a PNG written by encode_png (filter type 0 only) back to raw RGB."""
    chunks = read_chunks(data)
    width, height = struct.unpack(">II", chunks[0][1][:8])
    raw = zlib.decompress(b"".join(p for k, p in chunks if k == b"IDAT"))
    stride = width * 3
    rows = []
    for y in range(height):
        start = y * (stride + 1)
        if raw[start] != 0:
            raise ValueError("unsupported PNG filter")
        rows.append(raw[start + 1:start + 1 + stride])
    return width, height, b"".join(rows)
