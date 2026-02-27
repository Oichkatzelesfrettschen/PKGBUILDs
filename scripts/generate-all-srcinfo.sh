#!/bin/sh
# generate-all-srcinfo.sh -- Regenerate .SRCINFO for every PKGBUILD.
#
# WHY: .SRCINFO must be kept in sync with PKGBUILD for AUR submission.
#      After any pkgver/pkgrel/source/depends change, regenerate .SRCINFO.
#
# USAGE: sh scripts/generate-all-srcinfo.sh

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

OK=0
FAIL=0

echo "==> Regenerating .SRCINFO for all packages..."

fd -t f -g 'PKGBUILD' --max-depth 3 "${REPO_ROOT}" 2>/dev/null | while read -r pkgbuild; do
    dir=$(dirname "${pkgbuild}")
    pkg=$(basename "${dir}")
    if (cd "${dir}" && makepkg --printsrcinfo > .SRCINFO 2>/dev/null); then
        echo "  [OK] ${pkg}"
        OK=$((OK + 1))
    else
        echo "  [FAIL] ${pkg}"
        FAIL=$((FAIL + 1))
    fi
done

echo ""
echo "==> Done. Check output above for any failures."
echo "    Commit .SRCINFO changes with: git add '**/.SRCINFO' && git commit -m 'regen: update .SRCINFO files'"
