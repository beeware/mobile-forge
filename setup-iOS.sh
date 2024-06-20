# set -e

usage() {
    echo "Usage:"
    echo
    echo "    source $1 <python version>"
    echo
    echo "for example:"
    echo
    echo "    source $1 3.12"
    echo
}

# make sure the script is sourced
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    echo "This script must be sourced."
    echo
    usage $0
    exit 1
fi

if [ -z "$1" ]; then
    echo "Python version is not provided."
    echo
    usage $0
    return
fi

PYTHON_VER=$1
CMAKE_VERSION="3.27.4"

if [ -z "$PYTHON_APPLE_SUPPORT" ]; then
    echo "PYTHON_APPLE_SUPPORT not defined."
    return
fi

if [ ! -d $PYTHON_APPLE_SUPPORT/install ]; then
    echo "PYTHON_APPLE_SUPPORT does not point at a valid loation."
    return
fi

PYTHON_FOLDER=$(echo `ls -1d $PYTHON_APPLE_SUPPORT/install/macOS/macosx/python-$PYTHON_VER.*` | sort -n -r | head -n1)
PYTHON_VERSION=$(basename $PYTHON_FOLDER | cut -d "-" -f 2)

if [ ! -x $PYTHON_APPLE_SUPPORT/install/macOS/macosx/python-$PYTHON_VERSION/bin/python$PYTHON_VER ]; then
    echo "PYTHON_APPLE_SUPPORT does not appear to contain a Python $PYTHON_VERSION macOS binary."
    echo $PYTHON_APPLE_SUPPORT/install/macOS/macosx/python-$PYTHON_VERSION/bin/python$PYTHON_VER
    return
fi

if [ ! -e $PYTHON_APPLE_SUPPORT/install/iOS/iphoneos.arm64/python-$PYTHON_VERSION/bin/python$PYTHON_VER ]; then
    echo "PYTHON_APPLE_SUPPORT does not appear to contain a Python $PYTHON_VERSION iOS ARM64 device binary."
    return
fi

if [ ! -e $PYTHON_APPLE_SUPPORT/install/iOS/iphonesimulator.arm64/python-$PYTHON_VERSION/bin/python$PYTHON_VER ]; then
    echo "PYTHON_APPLE_SUPPORT does not appear to contain a Python $PYTHON_VERSION iOS ARM64 simulator binary."
    return
fi

if [ ! -e $PYTHON_APPLE_SUPPORT/install/iOS/iphonesimulator.x86_64/python-$PYTHON_VERSION/bin/python$PYTHON_VER ]; then
    echo "PYTHON_APPLE_SUPPORT does not appear to contain a Python $PYTHON_VERSION iOS x86-64 simulator binary."
    return
fi

# Ensure CMake is installed
if ! [ -d "tools/CMake.app" ]; then
    if ! [ -f "downloads/cmake-${CMAKE_VERSION}-macos-universal.tar.gz" ]; then
        echo "Downloading CMake"
        mkdir -p downloads
        curl --location "https://github.com/Kitware/CMake/releases/download/v${CMAKE_VERSION}/cmake-${CMAKE_VERSION}-macos-universal.tar.gz" --output downloads/cmake-${CMAKE_VERSION}-macos-universal.tar.gz
    fi

    echo "Installing CMake"
    mkdir -p tools
    tar -xzf downloads/cmake-${CMAKE_VERSION}-macos-universal.tar.gz
    mv cmake-${CMAKE_VERSION}-macos-universal/CMake.app tools
    rm -rf cmake-${CMAKE_VERSION}-macos-universal
fi

if [ ! -z "$VIRTUAL_ENV" ]; then
    deactivate
fi

if [ ! -d ./venv$PYTHON_VER ]; then
    echo "Creating Python $PYTHON_VER virtual environment for build..."
    $PYTHON_APPLE_SUPPORT/install/macOS/macosx/python-$PYTHON_VERSION/bin/python$PYTHON_VER -m venv venv$PYTHON_VER

    source ./venv$PYTHON_VER/bin/activate

    pip install -U pip
    pip install -e . wheel

    echo "Building platform dependency wheels..."
    python -m make_dep_wheels iOS
    if [ $? -ne 0 ]; then
        return
    fi

    echo "Python $PYTHON_VERSION environment has been created."
    echo
else
    echo "Using existing Python $PYTHON_VERSION environment."
    source ./venv$PYTHON_VER/bin/activate
fi

# Create wheels for ninja that can be installed in the host environment
if ! [ -f "dist/ninja-1.11.1-py3-none-ios_12_0_iphoneos_arm64.whl" ]; then
    echo "Downloading Ninja"
    python -m pip wheel --no-deps -w dist ninja==1.11.1
    mv dist/ninja-1.11.1-*.whl dist/ninja-1.11.1-py3-none-ios_12_0_iphoneos_arm64.whl
    cp dist/ninja-1.11.1-py3-none-ios_12_0_iphoneos_arm64.whl dist/ninja-1.11.1-py3-none-ios_12_0_iphonesimulator_x86_64.whl
    cp dist/ninja-1.11.1-py3-none-ios_12_0_iphoneos_arm64.whl dist/ninja-1.11.1-py3-none-ios_12_0_iphonesimulator_arm64.whl
fi

export PATH="$PATH:$PYTHON_APPLE_SUPPORT/support/$PYTHON_VER/iOS/bin:$(pwd)/tools/CMake.app/Contents/bin"

export MOBILE_FORGE_IPHONEOS_ARM64=$PYTHON_APPLE_SUPPORT/install/iOS/iphoneos.arm64/python-$PYTHON_VERSION/bin/python$PYTHON_VER
export MOBILE_FORGE_IPHONESIMULATOR_ARM64=$PYTHON_APPLE_SUPPORT/install/iOS/iphonesimulator.arm64/python-$PYTHON_VERSION/bin/python$PYTHON_VER
export MOBILE_FORGE_IPHONESIMULATOR_X86_64=$PYTHON_APPLE_SUPPORT/install/iOS/iphonesimulator.x86_64/python-$PYTHON_VERSION/bin/python$PYTHON_VER

# Setup docker for fortran/flang

if ! docker info &>/dev/null; then
  echo "Docker daemon not running!"
  exit 1
fi

export DOCKER_DEFAULT_PLATFORM=linux/amd64
# shellcheck disable=SC2048,SC2086
DOCKER_BUILDKIT=1 docker build -t flang --compress . $*
docker stop flang &>/dev/null || true
docker rm flang &>/dev/null || true
docker run -d --name flang -v "$(pwd)/share:/root/host" -v /Users:/Users -v /var/folders:/var/folders -it flang

# Print help

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
