import io
from os.path import dirname, join


def test_basic():
    from PIL import Image

    img = Image.open(join(dirname(__file__), "mandrill.jpg"))
    assert img.width == 512
    assert img.height == 512

    out_file = io.BytesIO()
    img.save(out_file, "png")
    out_bytes = out_file.getvalue()

    EXPECTED_LEN = 619474
    assert len(out_bytes) > int(EXPECTED_LEN * 0.8)
    assert len(out_bytes) < int(EXPECTED_LEN * 1.2)

    assert out_bytes[:24] == (
        b"\x89PNG\r\n\x1a\n"
        + b"\x00\x00\x00\rIHDR"  # File header
        + b"\x00\x00\x02\x00"  # Header chunk header
        + b"\x00\x00\x02\x00"  # Width 512  # Height 512
    )


def test_font():
    from PIL import ImageFont

    font = ImageFont.truetype(join(dirname(__file__), "Vera.ttf"), size=20)
    assert font.getbbox("Hello") == (0, 4, 51, 19)
    assert font.getbbox("Hello world") == (0, 4, 112, 19)
