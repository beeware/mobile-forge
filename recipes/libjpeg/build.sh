#!/bin/sh
set -eu

: "${PREFIX?ENV VAR MUST BE SET}"

# SIMD is only available for x86, so disable for consistency between ABIs.
./configure \
  --host="$HOST_TRIPLET" \
  --build="$BUILD_TRIPLET" \
  --without-turbojpeg \
  --without-simd
make -j "$CPU_COUNT"
make install prefix="$PREFIX"

rm -r "${PREFIX:?}/bin"
rm -r "$PREFIX/doc"
rm -r "$PREFIX/man"

mv "${PREFIX:?}/lib"?? "$PREFIX/lib"  # lib32 or lib64

rm -r "${PREFIX:?}/lib/pkgconfig"
find "${PREFIX:?}/lib/" -name "*.la" -exec rm -rf {} \;
