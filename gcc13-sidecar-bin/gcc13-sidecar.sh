#!/usr/bin/env bash
set -euo pipefail

export CC=/usr/bin/gcc-13
export CXX=/usr/bin/g++-13
export CPP=/usr/bin/cpp-13
export AR=/usr/bin/gcc-ar-13
export NM=/usr/bin/gcc-nm-13
export RANLIB=/usr/bin/gcc-ranlib-13

echo "gcc13 sidecar active: CC=${CC} CXX=${CXX}"
