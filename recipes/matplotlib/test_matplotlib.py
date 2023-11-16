def test_png(self):
    import io

    import matplotlib.pyplot as plt

    plt.figure()
    plt.plot([1, 2])
    bio = io.BytesIO()
    plt.savefig(bio, format="png")
    b = bio.getvalue()

    EXPECTED_LEN = 16782
    assert len(b) > int(EXPECTED_LEN * 0.8)
    assert len(b) < int(EXPECTED_LEN * 1.2)

    assert b[:24] == (
        b"\x89PNG\r\n\x1a\n"
        + b"\x00\x00\x00\rIHDR"  # File header
        + b"\x00\x00\x02\x80"  # Header chunk header
        + b"\x00\x00\x01\xe0"  # Width 640  # Height 480
    )
