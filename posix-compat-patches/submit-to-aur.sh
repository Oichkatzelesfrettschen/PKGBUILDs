#!/bin/sh
# Submit patched packages to AUR
# Prerequisites: SSH key must be added to your AUR account
#
# SSH key to add at https://aur.archlinux.org -> My Account -> SSH Public Key:
# ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIN3NBXC6bD1dQkSDgPYZdz/7Vama1u4zI4C4uWl1zaes eirikr-aur

set -e

BASEDIR="$(cd "$(dirname "$0")" && pwd)"
AURDIR="$BASEDIR/aur-repos"

mkdir -p "$AURDIR"
cd "$AURDIR"

echo "=== Submitting patches to AUR ==="
echo ""

submit_package() {
    pkg="$1"
    srcdir="$BASEDIR/$pkg"

    echo ">>> Processing $pkg"

    if [ ! -d "$pkg" ]; then
        echo "    Cloning from AUR..."
        git clone "ssh://aur@aur.archlinux.org/$pkg.git"
    else
        echo "    Updating existing clone..."
        cd "$pkg" && git pull && cd ..
    fi

    echo "    Copying files..."
    cp "$srcdir/PKGBUILD" "$pkg/"
    cp "$srcdir/.SRCINFO" "$pkg/"

    # Copy patches if they exist
    for patch in "$srcdir"/*.patch "$srcdir"/*.diff; do
        [ -f "$patch" ] && cp "$patch" "$pkg/"
    done

    # Copy additional source files
    for extra in "$srcdir/9" "$srcdir/plan9.sh"; do
        [ -f "$extra" ] && cp "$extra" "$pkg/"
    done

    cd "$pkg"
    git add -A

    if git diff --staged --quiet; then
        echo "    No changes to commit"
    else
        echo "    Committing changes..."
        git commit -m "Update for GCC 14/glibc 2.34 compatibility

Patches applied:
- Fix build errors with GCC 14 strict type checking
- Fix glibc 2.34+ SIGSTKSZ not being compile-time constant
- Fix C99 reserved keyword conflicts"

        echo "    Pushing to AUR..."
        git push
    fi

    cd "$AURDIR"
    echo ""
}

# Submit each package
submit_package "heirloom-sh"
submit_package "sbase-git"
submit_package "ubase-git"
submit_package "9base-git"

echo "=== AUR submission complete ==="
echo ""
echo "View your packages at:"
echo "  https://aur.archlinux.org/packages/heirloom-sh"
echo "  https://aur.archlinux.org/packages/sbase-git"
echo "  https://aur.archlinux.org/packages/ubase-git"
echo "  https://aur.archlinux.org/packages/9base-git"
