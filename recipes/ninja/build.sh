#!/bin/bash
set -eu

mkdir -p $PREFIX
rm -rf wheel/opt
mv ninja wheel
