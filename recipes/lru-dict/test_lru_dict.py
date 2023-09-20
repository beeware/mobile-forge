def test_basic():
    from lru import LRU

    data = LRU(3)
    data[1] = None
    data[2] = None
    data[3] = None
    data[1]
    data[4] = None
    assert data.keys == [4, 1, 3]
