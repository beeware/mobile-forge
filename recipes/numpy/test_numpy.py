def test_basic():
    from numpy import array

    assert (array([1, 2]) + array([3, 5])).tolist() == [4, 7]


def test_performance():
    from time import time

    import numpy as np

    start_time = time()
    SIZE = 500
    a = np.random.rand(SIZE, SIZE)
    b = np.random.rand(SIZE, SIZE)
    np.dot(a, b)

    # With OpenBLAS, the test devices take at most 0.4 seconds. Without OpenBLAS, they take
    # at least 1.0 seconds.
    duration = time() - start_time
    print(f"{duration:.3f}")
    assert duration < 0.7
