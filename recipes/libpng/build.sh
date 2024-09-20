#!/bin/sh
set -eu

: "${PREFIX?ENV VAR MUST BE SET}"

./configure --host="$HOST_TRIPLET" --build="$BUILD_TRIPLET"
make -j "$CPU_COUNT"
make install prefix="$PREFIX"

find "$PREFIX" -type l -print0 | xargs -0 rm

# do not unintentionally delete /bin
rm -r "${PREFIX:?}/bin"

mv "$PREFIX/include/libpng16/"* "$PREFIX/include"
rmdir "$PREFIX/include/libpng16"

# Some versions of Android (e.g. API level 26) have a libpng.so in /system/lib, but our copy
# has an SONAME of libpng16.so, so there's no conflict.
# find "${PREFIX:?}/lib/" -name '*.a' -exec rm -r {} +
# find "${PREFIX:?}/lib/" -name '*.la' -exec rm -r {} +
# rm -r "$PREFIX/lib/pkgconfig"

# Downstream recipes expect the name libpng.a, not libpng16.a
mv "$PREFIX/lib/libpng16.a" "$PREFIX/lib/libpng.a"

rm -r "$PREFIX/share"
