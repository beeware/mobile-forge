def test_basic(self):
    from lru import LRU

    data = LRU(3)
    data[1] = None
    data[2] = None
    data[3] = None
    data[1]
    data[4] = None
    self.assertEqual([4, 1, 3], data.keys())
