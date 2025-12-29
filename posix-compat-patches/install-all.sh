#!/bin/sh
# Install all POSIX compatibility packages
# Run: sudo sh install-all.sh

set -e

PKGDIR="/home/eirikr/makepkg-output/packages"

echo "Installing POSIX compatibility packages..."
echo ""

# Install sbase-git LAST to ensure dd/mknod are present
# (ubase-git removes duplicates during build to avoid conflicts)
pacman -U \
    "$PKGDIR/heirloom-sh-050706-5-x86_64.pkg.tar.zst" \
    "$PKGDIR/9base-git-20190913.117-2-x86_64.pkg.tar.zst" \
    "$PKGDIR/ubase-git-0.r616.ga570a80-1-x86_64.pkg.tar.zst" \
    "$PKGDIR/sbase-git-0.1.r121.gc11a21f-2-x86_64.pkg.tar.zst" \
    --noconfirm

echo ""
echo "Installed packages:"
pacman -Q heirloom-sh sbase-git ubase-git 9base-git

echo ""
echo "Validating installations..."
echo "Heirloom Shell: $(/usr/heirloom/bin/sh -c 'echo OK' 2>/dev/null || echo FAIL)"
echo "sbase ls: $(/opt/sbase/bin/ls / >/dev/null 2>&1 && echo OK || echo FAIL)"
echo "sbase dd: $(/opt/sbase/bin/dd if=/dev/zero of=/dev/null bs=1 count=1 2>/dev/null && echo OK || echo FAIL)"
echo "ubase free: $(/opt/sbase/bin/free >/dev/null 2>&1 && echo OK || echo FAIL)"
echo "9base echo: $(/opt/plan9/bin/echo OK 2>/dev/null || echo FAIL)"

echo ""
echo "Installation complete!"
