#!/bin/bash
set -eu

mkdir -p $PREFIX
cp -r ninja wheel

# Ensure the binary is executable
chmod +x wheel/ninja/data/bin/ninja

# Write the metadata for the entry point script
mkdir -p wheel/ninja-$VERSION.dist-info
cat << EOF > wheel/ninja-$VERSION.dist-info/entry_points.txt
[console_scripts]
ninja = ninja:ninja
EOF
