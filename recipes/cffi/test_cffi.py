def test_basic():
    from cffi import FFI

    ffi = FFI()
    ffi.cdef("size_t strlen(char *str);")
    lib = ffi.dlopen(None)
    assert lib.strlen(ffi.new("char[]", b"hello world")) == 11
