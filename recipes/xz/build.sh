#!/bin/sh
set -eu

: "${PREFIX?ENV VAR MUST BE SET}"

mkdir -p "$PREFIX"
cp -r include "$PREFIX"
cp -r lib "$PREFIX"

# Strip out any dylib files to ensure static linking
find "$PREFIX" -name "*.dylib" -exec rm -rf {} \;
