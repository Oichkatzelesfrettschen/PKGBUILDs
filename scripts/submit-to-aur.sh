#!/bin/sh
# submit-to-aur.sh -- Submit or update a package on the AUR.
#
# WHY: Automates the repetitive AUR submission workflow: clone the AUR repo,
#      copy the PKGBUILD and .SRCINFO, commit, and push. Requires an active
#      SSH key registered with AUR.
#
# USAGE: sh scripts/submit-to-aur.sh <package-dir> [--dry-run]
#
# REQUIREMENTS:
#   - SSH key configured for AUR: https://aur.archlinux.org/
#   - git configured with name and email
#   - The package directory must have both PKGBUILD and .SRCINFO

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
AUR_BASE="ssh://aur@aur.archlinux.org"
WORK_DIR="${REPO_ROOT}/posix-compat-patches/aur-repos"

DRY_RUN=0
PKG_DIR=""

for arg in "$@"; do
    case "${arg}" in
        --dry-run) DRY_RUN=1 ;;
        -*) echo "Unknown flag: ${arg}"; exit 1 ;;
        *) PKG_DIR="${arg}" ;;
    esac
done

if [ -z "${PKG_DIR}" ]; then
    echo "Usage: $0 <package-dir> [--dry-run]"
    echo ""
    echo "Examples:"
    echo "  $0 oterm"
    echo "  $0 posix-compat-patches/sbase-git --dry-run"
    exit 1
fi

# Resolve package directory
if [ -d "${REPO_ROOT}/${PKG_DIR}" ]; then
    ABS_PKG_DIR="${REPO_ROOT}/${PKG_DIR}"
elif [ -d "${PKG_DIR}" ]; then
    ABS_PKG_DIR="$(cd "${PKG_DIR}" && pwd)"
else
    echo "ERROR: Package directory not found: ${PKG_DIR}"
    exit 1
fi

if [ ! -f "${ABS_PKG_DIR}/PKGBUILD" ]; then
    echo "ERROR: No PKGBUILD in ${ABS_PKG_DIR}"
    exit 1
fi

if [ ! -f "${ABS_PKG_DIR}/.SRCINFO" ]; then
    echo "ERROR: No .SRCINFO in ${ABS_PKG_DIR}"
    echo "Generate it with: cd ${ABS_PKG_DIR} && makepkg --printsrcinfo > .SRCINFO"
    exit 1
fi

# Extract pkgname from .SRCINFO (more reliable than PKGBUILD parsing)
AUR_PKG=$(grep '^pkgbase\|^pkgname' "${ABS_PKG_DIR}/.SRCINFO" | head -1 | awk '{print $3}')
if [ -z "${AUR_PKG}" ]; then
    echo "ERROR: Could not determine pkgname from .SRCINFO"
    exit 1
fi

echo "==> Submitting: ${AUR_PKG}"
echo "    Source:     ${ABS_PKG_DIR}"
echo "    AUR URL:    ${AUR_BASE}/${AUR_PKG}.git"
if [ "${DRY_RUN}" -eq 1 ]; then
    echo "    Mode:       DRY RUN (no push)"
fi
echo ""

mkdir -p "${WORK_DIR}"
AUR_CLONE="${WORK_DIR}/${AUR_PKG}"

# Clone or update the AUR repo
if [ -d "${AUR_CLONE}/.git" ]; then
    echo "==> Updating existing clone..."
    git -C "${AUR_CLONE}" pull --rebase
else
    echo "==> Cloning AUR repo..."
    git clone "${AUR_BASE}/${AUR_PKG}.git" "${AUR_CLONE}" || {
        echo "==> (New package - initializing empty repo)"
        mkdir -p "${AUR_CLONE}"
        git -C "${AUR_CLONE}" init
        git -C "${AUR_CLONE}" remote add origin "${AUR_BASE}/${AUR_PKG}.git"
    }
fi

# Copy PKGBUILD, .SRCINFO, and any .install files
echo "==> Copying package files..."
cp "${ABS_PKG_DIR}/PKGBUILD" "${AUR_CLONE}/PKGBUILD"
cp "${ABS_PKG_DIR}/.SRCINFO" "${AUR_CLONE}/.SRCINFO"

# Copy .install file if present
for f in "${ABS_PKG_DIR}"/*.install; do
    [ -f "${f}" ] && cp "${f}" "${AUR_CLONE}/" && echo "    Copied: $(basename "${f}")"
done

# Stage and commit
VERSION=$(grep '^pkgver' "${AUR_CLONE}/.SRCINFO" | head -1 | awk '{print $3}')
PKGREL=$(grep '^pkgrel' "${AUR_CLONE}/.SRCINFO" | head -1 | awk '{print $3}')

echo "==> Staging changes..."
git -C "${AUR_CLONE}" add PKGBUILD .SRCINFO
for f in "${AUR_CLONE}"/*.install; do
    [ -f "${f}" ] && git -C "${AUR_CLONE}" add "$(basename "${f}")"
done

if git -C "${AUR_CLONE}" diff --cached --quiet; then
    echo "==> No changes to commit. Already up to date."
    exit 0
fi

COMMIT_MSG="Update to ${VERSION}-${PKGREL}"
echo "==> Committing: ${COMMIT_MSG}"
git -C "${AUR_CLONE}" commit -m "${COMMIT_MSG}"

if [ "${DRY_RUN}" -eq 1 ]; then
    echo "==> [DRY RUN] Would push to AUR"
    echo "    Run without --dry-run to push"
else
    echo "==> Pushing to AUR..."
    git -C "${AUR_CLONE}" push origin master
    echo "==> Done: https://aur.archlinux.org/packages/${AUR_PKG}"
fi
