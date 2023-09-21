def test_einsum():
    import numpy as np
    from blis.py import einsum

    a = np.array([[1.0, 2.0], [3.0, 4.0]])
    b = np.array([[2.0, 3.0], [5.0, 7.0]])
    np.testing.assert_equal(
        np.array([[12.0, 17.0], [26.0, 37.0]]), einsum("ab,bc->ac", a, b)
    )
