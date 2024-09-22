#!/bin/sh
set -eu

: "${PREFIX?ENV VAR MUST BE SET}"

./configure \
    --host="$HOST_TRIPLET" \
    --build="$BUILD_TRIPLET" \
    --enable-static \
    --without-harfbuzz \
    --without-png \
    BZIP2_CFLAGS="-I$INSTALL_ROOT/include" \
    BZIP2_LIBS="-L$INSTALL_ROOT/lib -lbz2" \
    ZLIB_CFLAGS="-I$INSTALL_ROOT/include" \
    ZLIB_LIBS="-L$INSTALL_ROOT/lib -lz"

make -j "$CPU_COUNT"
make install prefix="$PREFIX"

mv "$PREFIX/include/freetype2/"* "$PREFIX/include"
rmdir "$PREFIX/include/freetype2"

# Some versions of Android (e.g. API level 26) have a libft2.so in /system/lib, but our copy
# has an SONAME of libfreetype.so, so there's no conflict.
# find "${PREFIX:?}/lib/" -name "*.a" -exec rm -rf {} \;
find "${PREFIX:?}/lib/" -name "*.la" -exec rm -rf {} \;
rm -r "${PREFIX:?}/lib/pkgconfig"
rm -r "${PREFIX:?}/share"
