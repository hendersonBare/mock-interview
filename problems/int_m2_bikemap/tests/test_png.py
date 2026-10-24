import pytest

from bikemap.png import SIGNATURE, decode_rgb, encode_png, png_info, read_chunks


def test_roundtrip_pixels_and_text():
    rgb = bytes([255, 0, 0, 0, 255, 0, 0, 0, 255, 10, 20, 30])
    data = encode_png(2, 2, rgb, {"note": "hello"})
    assert data.startswith(SIGNATURE)
    assert decode_rgb(data) == (2, 2, rgb)
    info = png_info(data)
    assert (info.width, info.height, info.text) == (2, 2, {"note": "hello"})


def test_chunk_order():
    kinds = [k for k, _ in read_chunks(encode_png(1, 1, b"\x00\x00\x00", {"a": "b"}))]
    assert kinds == [b"IHDR", b"tEXt", b"IDAT", b"IEND"]


def test_corruption_is_detected():
    data = bytearray(encode_png(1, 1, b"\x01\x02\x03"))
    data[-20] ^= 0xFF
    with pytest.raises(ValueError):
        read_chunks(bytes(data))


def test_not_png():
    with pytest.raises(ValueError):
        png_info(b"GIF89a....")


def test_buffer_size_checked():
    with pytest.raises(ValueError):
        encode_png(2, 2, b"\x00" * 3)
