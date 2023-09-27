#!/bin/bash
# set -e

if [ -z "$1" ]; then
    echo "usage: $0 <python version>"
    echo "e.g.:"
    echo
    echo "    source $0 3.11"
    echo
    exit 1
fi
PYTHON_VER=$1

if [ -z "$PYTHON_APPLE_SUPPORT" ]; then
    echo "PYTHON_APPLE_SUPPORT not defined."
    exit 1
fi

if [ ! -d $PYTHON_APPLE_SUPPORT/install ]; then
    echo "PYTHON_APPLE_SUPPORT does not point at a valid loation."
    exit 1
fi

PYTHON_FOLDER=$(echo `ls -1d $PYTHON_APPLE_SUPPORT/install/macOS/macosx/python-$PYTHON_VER.*` | sort -n -r | head -n1)
PYTHON_VERSION=$(basename $PYTHON_FOLDER | cut -d "-" -f 2)

if [ ! -x $PYTHON_APPLE_SUPPORT/install/macOS/macosx/python-$PYTHON_VERSION/bin/python$PYTHON_VER ]; then
    echo "PYTHON_APPLE_SUPPORT does not appear to contain a Python $PYTHON_VERSION macOS binary."
    echo $PYTHON_APPLE_SUPPORT/install/macOS/macosx/python-$PYTHON_VERSION/bin/python$PYTHON_VER
    exit 1
fi

if [ ! -e $PYTHON_APPLE_SUPPORT/install/iOS/iphoneos.arm64/python-$PYTHON_VERSION/bin/python$PYTHON_VER ]; then
    echo "PYTHON_APPLE_SUPPORT does not appear to contain a Python $PYTHON_VERSION iOS ARM64 device binary."
    exit 1
fi

if [ ! -e $PYTHON_APPLE_SUPPORT/install/iOS/iphonesimulator.arm64/python-$PYTHON_VERSION/bin/python$PYTHON_VER ]; then
    echo "PYTHON_APPLE_SUPPORT does not appear to contain a Python $PYTHON_VERSION iOS ARM64 simulator binary."
    exit 1
fi

if [ ! -e $PYTHON_APPLE_SUPPORT/install/iOS/iphonesimulator.x86_64/python-$PYTHON_VERSION/bin/python$PYTHON_VER ]; then
    echo "PYTHON_APPLE_SUPPORT does not appear to contain a Python $PYTHON_VERSION iOS x86-64 simulator binary."
    exit 1
fi

if [ ! -z "$VIRTUAL_ENV" ]; then
    deactivate
fi

if [ ! -d ./venv$PYTHON_VER ]; then
    echo "Creating Python $PYTHON_VER virtual environment for build..."
    $PYTHON_APPLE_SUPPORT/install/macOS/macosx/python-$PYTHON_VERSION/bin/python$PYTHON_VER -m venv venv$PYTHON_VER

    echo "Copying platform wheels..."
    mkdir -p dist
    cp $PYTHON_APPLE_SUPPORT/wheels/iOS/* dist

    source ./venv$PYTHON_VER/bin/activate

    pip install -U pip
    pip install -e .

    echo "Python $PYTHON_VERSION environment has been created."
    echo
else
    echo "Using existing Python $PYTHON_VERSION environment."
    source ./venv$PYTHON_VER/bin/activate
fi

export PATH=$PATH:$PYTHON_APPLE_SUPPORT/install/iOS/bin

export MOBILE_FORGE_IPHONEOS_ARM64=$PYTHON_APPLE_SUPPORT/install/iOS/iphoneos.arm64/python-$PYTHON_VERSION/bin/python$PYTHON_VER
export MOBILE_FORGE_IPHONESIMULATOR_ARM64=$PYTHON_APPLE_SUPPORT/install/iOS/iphonesimulator.arm64/python-$PYTHON_VERSION/bin/python$PYTHON_VER
export MOBILE_FORGE_IPHONESIMULATOR_X86_64=$PYTHON_APPLE_SUPPORT/install/iOS/iphonesimulator.x86_64/python-$PYTHON_VERSION/bin/python$PYTHON_VER

echo
echo "You can now build packages with forge; e.g.:"
echo
echo "Build all packages for all iOS targets:"
echo "   forge iOS"
echo
echo "Build only the non-python packages, for all iOS targets:"
echo "   forge iOS -s non-py"
echo
echo "Build all packages needed for a smoke test, for all iOS targets:"
echo "   forge iOS -s smoke"
echo
echo "Build lru-dict for all iOS targets:"
echo "   forge iOS lru-dict"
echo
echo "Build lru-dict for the ARM64 device target:"
echo "   forge iphoneos:arm64 lru-dict"
echo
