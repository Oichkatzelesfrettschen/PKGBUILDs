# Makefile for building IA-16 toolchain PKGBUILDs
# Usage: make all          - Build and install all packages
#        make binutils     - Build binutils only
#        make gcc-stage1   - Build stage1 GCC only
#        make newlib       - Build newlib only
#        make gcc          - Build full GCC (stage2)
#        make clean        - Clean all build artifacts

.PHONY: all binutils gcc-stage1 newlib gcc clean help

MAKEPKG_FLAGS ?= -si --noconfirm

all: gcc
	@echo "=== IA-16 toolchain installation complete ==="
	@echo "Toolchain installed to /opt/ia16"
	@echo "Add to PATH: export PATH=/opt/ia16/bin:\$$PATH"

binutils:
	@echo "=== Building binutils-ia16-custom ==="
	cd binutils-ia16-custom && makepkg $(MAKEPKG_FLAGS)

gcc-stage1: binutils
	@echo "=== Building gcc-ia16-custom-stage1 ==="
	cd gcc-ia16-custom-stage1 && makepkg $(MAKEPKG_FLAGS)

newlib: gcc-stage1
	@echo "=== Building newlib-ia16-custom ==="
	cd newlib-ia16-custom && makepkg $(MAKEPKG_FLAGS)

gcc: newlib
	@echo "=== Building gcc-ia16-custom (full) ==="
	cd gcc-ia16-custom && makepkg $(MAKEPKG_FLAGS)

meta: gcc
	@echo "=== Installing meta-package ==="
	cd ia16-toolchain-meta && makepkg $(MAKEPKG_FLAGS)

clean:
	@echo "=== Cleaning build artifacts ==="
	rm -rf binutils-ia16-custom/src binutils-ia16-custom/pkg binutils-ia16-custom/*.pkg.tar.zst
	rm -rf gcc-ia16-custom-stage1/src gcc-ia16-custom-stage1/pkg gcc-ia16-custom-stage1/*.pkg.tar.zst
	rm -rf newlib-ia16-custom/src newlib-ia16-custom/pkg newlib-ia16-custom/*.pkg.tar.zst
	rm -rf gcc-ia16-custom/src gcc-ia16-custom/pkg gcc-ia16-custom/*.pkg.tar.zst
	rm -rf ia16-toolchain-meta/pkg ia16-toolchain-meta/*.pkg.tar.zst

help:
	@echo "IA-16 Toolchain PKGBUILD Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  all         - Build and install complete toolchain (default)"
	@echo "  binutils    - Build binutils-ia16-custom only"
	@echo "  gcc-stage1  - Build bootstrap GCC (no libc)"
	@echo "  newlib      - Build newlib C library"
	@echo "  gcc         - Build full GCC with libc support"
	@echo "  meta        - Install meta-package"
	@echo "  clean       - Remove build artifacts"
	@echo ""
	@echo "Variables:"
	@echo "  MAKEPKG_FLAGS - Flags for makepkg (default: -si --noconfirm)"
	@echo ""
	@echo "Build order: binutils -> gcc-stage1 -> newlib -> gcc"
