#!/bin/sh
# Install all POSIX compatibility packages from a local package directory.
#
# WHY: Provides an easy way to bulk-install the posix-compat-patches packages
#      after building them with makepkg. The package directory and versions are
#      configurable so this script works across machines.
#
# USAGE: PKGDIR=/path/to/packages sh install-all.sh
#        Or run with defaults which use the current directory.

set -eu

# Default to current directory if PKGDIR is not set in the environment.
PKGDIR="${PKGDIR:-$(pwd)}"

# Verify the directory exists
if [ ! -d "${PKGDIR}" ]; then
    echo "ERROR: Package directory not found: ${PKGDIR}"
    echo "Set PKGDIR to the directory containing the built .pkg.tar.zst files"
    exit 1
fi

echo "Installing POSIX compatibility packages from: ${PKGDIR}"
echo ""

# Find packages by glob rather than hardcoded filenames.
# Install sbase-git LAST: ubase-git removes duplicate commands (dd, mknod)
# during its own build to avoid file conflicts with sbase-git.
SUDO_ASKPASS=/usr/bin/unified-askpass sudo -A pacman -U \
    "${PKGDIR}"/heirloom-sh-*.pkg.tar.zst \
    "${PKGDIR}"/9base-git-*.pkg.tar.zst \
    "${PKGDIR}"/ubase-git-*.pkg.tar.zst \
    "${PKGDIR}"/sbase-git-*.pkg.tar.zst \
    --noconfirm

echo ""
echo "Installed packages:"
pacman -Q heirloom-sh sbase-git ubase-git 9base-git

echo ""
echo "Validating installations..."
echo "Heirloom Shell: $(/usr/heirloom/bin/sh -c 'echo OK' 2>/dev/null || echo FAIL)"
echo "sbase ls:       $(/opt/sbase/bin/ls / > /dev/null 2>&1 && echo OK || echo FAIL)"
echo "sbase dd:       $(/opt/sbase/bin/dd if=/dev/zero of=/dev/null bs=1 count=1 2>/dev/null && echo OK || echo FAIL)"
echo "9base echo:     $(/opt/plan9/bin/echo OK 2>/dev/null || echo FAIL)"

echo ""
echo "Installation complete!"
