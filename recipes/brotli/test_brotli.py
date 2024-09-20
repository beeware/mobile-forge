def test_basic():
    import brotli

    plain = b"it was the best of times, it was the worst of times"
    compressed = brotli.compress(plain)

    assert len(compressed) < len(plain)
    assert plain == brotli.decompress(compressed)
