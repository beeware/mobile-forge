# See https://github.com/ilanschnell/bitarray/blob/master/README.md
def test_basic():
    from bitarray import bitarray

    a = bitarray()
    a.append(True)
    a.extend([False, True, True])
    assert a == bitarray("1011")
    assert a != bitarray("1111")

    b = bitarray("1100")
    assert a & b == bitarray("1000")
    assert a | b == bitarray("1111")
    assert a ^ b == bitarray("0111")

    a[:] = True
    assert a == bitarray("1111")
