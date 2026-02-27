#!/bin/sh
# check-updates.sh -- Check for upstream version updates across all packages.
#
# WHY: Keeping package versions current is a maintenance responsibility.
#      This script queries PyPI, GitHub releases, and other sources to report
#      which packages have newer versions available.
#
# USAGE: sh scripts/check-updates.sh [--verbose]
#
# REQUIREMENTS: curl, jq (for JSON parsing)
#
# OUTPUT: Prints packages where a newer upstream version may be available.

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

VERBOSE=0
for arg in "$@"; do
    case "${arg}" in
        --verbose|-v) VERBOSE=1 ;;
        *) echo "Unknown argument: ${arg}"; exit 1 ;;
    esac
done

log() {
    if [ "${VERBOSE}" -eq 1 ]; then
        echo "  [verbose] $*"
    fi
}

check_pypi() {
    local pkgname="$1"
    local current="$2"
    local pypi_name="$3"

    latest=$(curl -sf "https://pypi.org/pypi/${pypi_name}/json" 2>/dev/null \
        | grep -o '"version": *"[^"]*"' | head -1 | grep -o '"[^"]*"$' | tr -d '"') || {
        log "PyPI query failed for ${pypi_name}"
        return
    }

    if [ -n "${latest}" ] && [ "${latest}" != "${current}" ]; then
        printf "  %-40s current=%-15s latest=%s (PyPI)\n" "${pkgname}" "${current}" "${latest}"
    else
        log "${pkgname}: ${current} is current (PyPI)"
    fi
}

check_github() {
    local pkgname="$1"
    local current="$2"
    local repo="$3"  # e.g. "owner/repo"

    latest=$(curl -sf "https://api.github.com/repos/${repo}/releases/latest" 2>/dev/null \
        | grep -o '"tag_name": *"[^"]*"' | head -1 | grep -o '"[^"]*"$' | tr -d '"v"') || {
        log "GitHub query failed for ${repo}"
        return
    }

    if [ -n "${latest}" ] && [ "${latest}" != "${current}" ]; then
        printf "  %-40s current=%-15s latest=%s (GitHub)\n" "${pkgname}" "${current}" "${latest}"
    else
        log "${pkgname}: ${current} is current (GitHub)"
    fi
}

get_pkgver() {
    grep '^pkgver=' "$1" | head -1 | cut -d= -f2 | tr -d "'"
}

echo "==> Checking for upstream version updates..."
echo "    (requires network access)"
echo ""

# Python packages (PyPI)
echo "--- Python packages (PyPI) ---"
check_pypi "python-pdfplumber" "$(get_pkgver "${REPO_ROOT}/python-pdfplumber/PKGBUILD")" "pdfplumber"
check_pypi "python-pillow6" "$(get_pkgver "${REPO_ROOT}/python-pillow6/PKGBUILD")" "pillow"
check_pypi "python-sse-starlette" "$(get_pkgver "${REPO_ROOT}/python-sse-starlette/PKGBUILD")" "sse-starlette"
check_pypi "python-asgi-lifespan" "$(get_pkgver "${REPO_ROOT}/python-asgi-lifespan/PKGBUILD")" "asgi-lifespan"
check_pypi "python-backports-zstd" "$(get_pkgver "${REPO_ROOT}/python-backports-zstd/PKGBUILD")" "backports-zstd"
check_pypi "python-pypdfium2" "$(get_pkgver "${REPO_ROOT}/python-pypdfium2/PKGBUILD")" "pypdfium2"

echo ""
echo "--- GitHub releases ---"
check_github "tla-plus-toolbox" "$(get_pkgver "${REPO_ROOT}/tla-plus-toolbox/PKGBUILD")" "tlaplus/tlaplus"
check_github "oterm" "$(get_pkgver "${REPO_ROOT}/oterm/PKGBUILD")" "ggozad/oterm"
check_github "yay" "$(get_pkgver "${REPO_ROOT}/yay/PKGBUILD")" "Jguer/yay"

echo ""
echo "--- Cross-compiler toolchains (manual check recommended) ---"
for f in "${REPO_ROOT}"/m68k-elf-gcc/PKGBUILD \
         "${REPO_ROOT}"/i386-elf-gcc/PKGBUILD \
         "${REPO_ROOT}"/msp430-elf-gcc/PKGBUILD; do
    [ -f "$f" ] && printf "  %-40s pkgver=%s\n" "$(basename "$(dirname "$f")")" "$(get_pkgver "$f")"
done
echo "  Check https://ftp.gnu.org/gnu/gcc/ for latest GCC release"

echo ""
echo "==> Note: VCS packages (git+) always fetch latest on build."
echo "    Review -git packages manually for API/interface changes."
