#!/bin/sh
set -e

usage() {
    echo "Usage:"
    echo
    echo "    source $1 <python version> [<support revision>]"
    echo
    echo "for example:"
    echo
    echo "    source $1 3.12"
    echo "    source $1 3.12 3"
    echo
}

# make sure the script is sourced (https://stackoverflow.com/a/28776166/8549606)
SOURCED=0
if [ -n "$ZSH_VERSION" ]; then
  case $ZSH_EVAL_CONTEXT in *:file) SOURCED=1;; esac
elif [ -n "$KSH_VERSION" ]; then
  # shellcheck disable=SC2296
  [ "$(cd -- "$(dirname -- "$0")" && pwd -P)/$(basename -- "$0")" != "$(cd -- "$(dirname -- "${.sh.file}")" && pwd -P)/$(basename -- "${.sh.file}")" ] && SOURCED=1
elif [ -n "$BASH_VERSION" ]; then
  (return 0 2>/dev/null) && SOURCED=1
else # All other shells: examine $0 for known shell binary filenames.
  # Detects `sh` and `dash`; add additional shell filenames as needed.
  case ${0##*/} in sh|-sh|dash|-dash) SOURCED=1;; esac
fi

if [ "$SOURCED" = "0" ]; then
    echo "This script must be sourced."
    echo
    usage "$0"
    exit 1
fi

if [ -z "$1" ]; then
    echo "Python version is not provided."
    echo
    usage "$0"
    return
fi

PYTHON_VER=$1

if [ -n "$VIRTUAL_ENV" ]; then
    echo "A virtual environment is already active; deactivate that environment before calling this script."
    return
fi

# Create directories required by the script
mkdir -p deps
mkdir -p dist
mkdir -p downloads
mkdir -p published

if [ -z "$PYTHON_APPLE_SUPPORT" ]; then
    MOBILE_FORGE_SUPPORT_PATH="$(pwd)/support"
    export MOBILE_FORGE_SUPPORT_PATH

    if [ ! -d "$MOBILE_FORGE_SUPPORT_PATH/$PYTHON_VER/iOS" ]; then
        if [ -z "$2" ]; then
            case $PYTHON_VER in
                3.9)  SUPPORT_REVISION=14 ;;
                3.10) SUPPORT_REVISION=10 ;;
                3.11) SUPPORT_REVISION=5 ;;
                3.12) SUPPORT_REVISION=5 ;;
                3.13) SUPPORT_REVISION=2 ;;
                *)
                    echo "No default support revision for $PYTHON_VER is known; it must be specified manually"
                    return
                    ;;
            esac
        else
            SUPPORT_REVISION=$2
        fi

        if [ ! -e "downloads/Python-${PYTHON_VER}-iOS-support.b${SUPPORT_REVISION}.tar.gz" ]; then
            echo "Downloading Python ${PYTHON_VER} b${SUPPORT_REVISION} support package"
            curl \
              --location "https://github.com/beeware/Python-Apple-support/releases/download/${PYTHON_VER}-b${SUPPORT_REVISION}/Python-${PYTHON_VER}-iOS-support.b${SUPPORT_REVISION}.tar.gz" \
              --output "downloads/Python-${PYTHON_VER}-iOS-support.b${SUPPORT_REVISION}.tar.gz"
        fi

        echo "Unpacking Python ${PYTHON_VER} b${SUPPORT_REVISION} support package"
        mkdir -p "$MOBILE_FORGE_SUPPORT_PATH/$PYTHON_VER/iOS"
        cd "$MOBILE_FORGE_SUPPORT_PATH/$PYTHON_VER/iOS"
        tar zxf "../../../downloads/Python-${PYTHON_VER}-iOS-support.b${SUPPORT_REVISION}.tar.gz"
        cd -
    fi
else
    export MOBILE_FORGE_SUPPORT_PATH="$PYTHON_APPLE_SUPPORT/support"
fi
echo "Using $MOBILE_FORGE_SUPPORT_PATH as the support folder"

BUILD_PYTHON=$(which "python$PYTHON_VER")
if [ -z "$BUILD_PYTHON" ]; then
    echo "Can't find a Python $PYTHON_VER binary on the path."
    return
fi

if [ ! -e "$MOBILE_FORGE_SUPPORT_PATH/$PYTHON_VER/iOS/Python.xcframework/ios-arm64/bin/python$PYTHON_VER" ]; then
    echo "Support folder does not appear to contain a Python $PYTHON_VER iOS device binary."
    return
fi

if [ ! -e "$MOBILE_FORGE_SUPPORT_PATH/$PYTHON_VER/iOS/Python.xcframework/ios-arm64_x86_64-simulator/bin/python$PYTHON_VER" ]; then
    echo "Support folder does not appear to contain a Python $PYTHON_VER iOS simulator binary."
    return
fi

if [ ! -d "./venv$PYTHON_VER" ]; then
    echo "Creating Python $PYTHON_VER virtual environment for build..."
    echo "Using $BUILD_PYTHON as the build python"
    $BUILD_PYTHON -m venv "venv$PYTHON_VER"

    # shellcheck disable=SC1090
    . "./venv$PYTHON_VER/bin/activate"

    # Install basic environment artefacts
    pip install -U pip
    pip install -U setuptools wheel
    pip install -e .

    echo "Python $PYTHON_VER environment has been created."
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
    echo "Build all applicable versions of lru-dict for all iOS targets:"
    echo "   forge iOS --all-versions lru-dict"
    echo
else
    echo "Using existing Python $PYTHON_VER environment."
    # shellcheck disable=SC1090
    . "./venv$PYTHON_VER/bin/activate"
fi

# Disable exit on error
set +e
