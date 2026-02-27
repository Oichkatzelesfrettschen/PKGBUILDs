#!/bin/sh
# validate-all.sh -- Run namcap and makepkg --printsrcinfo on every PKGBUILD.
#
# WHY: Provides a fast, automated way to catch packaging errors (namcap) and
#      verify all PKGBUILDs can produce valid .SRCINFO output before committing.
#
# USAGE: sh scripts/validate-all.sh [--fix-srcinfo]
#
# OPTIONS:
#   --fix-srcinfo   Regenerate .SRCINFO for every package (in addition to checking)
#
# EXIT CODES:
#   0   All checks passed
#   1   One or more checks failed

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

FIX_SRCINFO=0
for arg in "$@"; do
    case "${arg}" in
        --fix-srcinfo) FIX_SRCINFO=1 ;;
        *) echo "Unknown argument: ${arg}"; exit 1 ;;
    esac
done

ERRORS=0
WARNINGS=0
CHECKED=0

echo "==> Validating PKGBUILDs in ${REPO_ROOT}"
echo ""

# Collect all PKGBUILD paths up to depth 3 (handles ia16-toolchain subdirs)
PKGBUILDS=$(cd "${REPO_ROOT}" && fd -t f -g 'PKGBUILD' --max-depth 3 . 2>/dev/null \
    || find . -maxdepth 3 -name PKGBUILD)

for pkgbuild in ${PKGBUILDS}; do
    dir="${REPO_ROOT}/$(dirname "${pkgbuild}")"
    pkg=$(basename "$(dirname "${pkgbuild}")")

    echo "--- ${pkg} ---"
    CHECKED=$((CHECKED + 1))

    # namcap check
    namcap_out=$(namcap "${dir}/PKGBUILD" 2>&1)
    if echo "${namcap_out}" | grep -q ' E: '; then
        echo "  [ERROR] namcap errors:"
        echo "${namcap_out}" | grep ' E: ' | sed 's/^/    /'
        ERRORS=$((ERRORS + 1))
    fi
    if echo "${namcap_out}" | grep -q ' W: '; then
        echo "  [WARN] namcap warnings:"
        echo "${namcap_out}" | grep ' W: ' | sed 's/^/    /'
        WARNINGS=$((WARNINGS + 1))
    fi

    # printsrcinfo check
    if ! (cd "${dir}" && makepkg --printsrcinfo > /dev/null 2>&1); then
        echo "  [ERROR] makepkg --printsrcinfo failed"
        ERRORS=$((ERRORS + 1))
    fi

    # Optionally regenerate .SRCINFO
    if [ "${FIX_SRCINFO}" -eq 1 ]; then
        (cd "${dir}" && makepkg --printsrcinfo > .SRCINFO 2>/dev/null) && \
            echo "  [OK] .SRCINFO regenerated" || \
            echo "  [ERROR] .SRCINFO generation failed"
    else
        # Check .SRCINFO presence
        if [ ! -f "${dir}/.SRCINFO" ]; then
            echo "  [WARN] .SRCINFO missing (run with --fix-srcinfo to generate)"
            WARNINGS=$((WARNINGS + 1))
        fi
    fi
done

echo ""
echo "==> Summary: ${CHECKED} packages checked, ${ERRORS} errors, ${WARNINGS} packages with warnings"

if [ "${ERRORS}" -gt 0 ]; then
    exit 1
fi
