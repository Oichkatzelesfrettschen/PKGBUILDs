#!/bin/sh
# build-pkg.sh -- Consistent wrapper around makepkg for building a single package.
#
# WHY: Ensures every package is built with the same directory layout for output,
#      sources, and logs; and runs namcap on the result to catch packaging issues.
#
# USAGE: sh scripts/build-pkg.sh <package-dir> [extra-makepkg-flags...]
#
# EXAMPLES:
#   sh scripts/build-pkg.sh oterm
#   sh scripts/build-pkg.sh i386-elf-gcc --skippgpcheck
#   sh scripts/build-pkg.sh ia16-toolchain/gcc-ia16-custom
#
# OUTPUT DIRECTORIES (relative to repo root):
#   build/packages/   Built package archives
#   build/sources/    Downloaded source tarballs
#   build/logs/       Per-package build logs

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <package-dir> [extra-makepkg-flags...]"
    exit 1
fi

PKG_DIR="${1}"; shift
BUILD_ROOT="${REPO_ROOT}/build"
PKGDEST="${BUILD_ROOT}/packages"
SRCDEST="${BUILD_ROOT}/sources"
LOGDEST="${BUILD_ROOT}/logs"

mkdir -p "${PKGDEST}" "${SRCDEST}" "${LOGDEST}"

# Resolve absolute path to the package directory
if [ -d "${REPO_ROOT}/${PKG_DIR}" ]; then
    ABS_PKG_DIR="${REPO_ROOT}/${PKG_DIR}"
elif [ -d "${PKG_DIR}" ]; then
    ABS_PKG_DIR="$(cd "${PKG_DIR}" && pwd)"
else
    echo "ERROR: Package directory not found: ${PKG_DIR}"
    exit 1
fi

if [ ! -f "${ABS_PKG_DIR}/PKGBUILD" ]; then
    echo "ERROR: No PKGBUILD found in ${ABS_PKG_DIR}"
    exit 1
fi

PKG_NAME=$(basename "${ABS_PKG_DIR}")
echo "==> Building: ${PKG_NAME}"
echo "    Output:   ${PKGDEST}"
echo "    Sources:  ${SRCDEST}"
echo "    Logs:     ${LOGDEST}"
echo ""

# Build the package
(cd "${ABS_PKG_DIR}" && \
    PKGDEST="${PKGDEST}" \
    SRCDEST="${SRCDEST}" \
    LOGDEST="${LOGDEST}" \
    makepkg --syncdeps --clean --log "$@")

# Run namcap on the resulting package
echo ""
echo "==> Running namcap on built package..."
for pkg in "${PKGDEST}"/${PKG_NAME}-*.pkg.tar.*; do
    [ -f "${pkg}" ] || continue
    echo "    ${pkg}"
    namcap "${pkg}" || true
done

echo ""
echo "==> Build complete: ${PKG_NAME}"
