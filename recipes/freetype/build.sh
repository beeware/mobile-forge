#!/bin/bash
set -eu

./configure \
    --host=$HOST_TRIPLET \
    --build=$BUILD_TRIPLET \
    --enable-static \
    --without-harfbuzz \
    --without-png \
    BZIP2_CFLAGS="-I$INSTALL_ROOT/include" \
    BZIP2_LIBS="-L$INSTALL_ROOT/lib -lbz2" \
    ZLIB_CFLAGS="-I$INSTALL_ROOT/include" \
    ZLIB_LIBS="-L$INSTALL_ROOT/lib -lz"

make -j $CPU_COUNT
make install prefix=$PREFIX

mv $PREFIX/include/freetype2/* $PREFIX/include
rmdir $PREFIX/include/freetype2

# Some versions of Android (e.g. API level 26) have a libft2.so in /system/lib, but our copy
# has an SONAME of libfreetype.so, so there's no conflict.
# rm -r $PREFIX/lib/{*.a,*.la,pkgconfig}
rm -r $PREFIX/lib/{*.la,pkgconfig}

rm -r $PREFIX/share
