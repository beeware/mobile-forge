#!/bin/bash
set -eu

mkdir -p $PREFIX
cp -r include $PREFIX
cp -r lib $PREFIX

# Strip out any dylib files to ensure static linking
find $PREFIX -name "*.dylib" -exec rm -rf {} \;
