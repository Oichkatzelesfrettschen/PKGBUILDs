# pkgbuilds - Project AI Context

## Overview

Arch Linux PKGBUILD collection: cross-compiler toolchains (~38 packages, 12
architectures), Python packages (9), dev tools (4), themes (4), system config
(2), POSIX compat patches (6), and misc utilities (6).

## Build Commands

```sh
# Validate all PKGBUILDs (namcap + printsrcinfo)
sh scripts/validate-all.sh

# Regenerate all .SRCINFO files
sh scripts/validate-all.sh --fix-srcinfo

# Build a single package (wrapper with consistent dirs + namcap)
sh scripts/build-pkg.sh <package-dir>

# Build a cross-compiler toolchain (example)
make -f Makefile.m68k all
cd ia16-toolchain && make all
```

## Standards

- **Checksums**: sha256sums (not md5sums). VCS sources use SKIP; all others
  need real sums. Run `updpkgsums` before committing.
- **Licenses**: SPDX identifiers (Arch RFC 0016). Use `GPL-3.0-or-later`,
  `MIT`, `BSD-3-Clause` etc., not `GPL`, `GPL3`, `BSD`.
- **Maintainer**: Use `eirikr <eirikr@localhost>` for self-authored packages.
- **SRCINFO**: Every PKGBUILD directory must have a `.SRCINFO` file tracked in
  git. Never add `.SRCINFO` to `.gitignore`.
- **PKGEXT**: Do not set `PKGEXT` inside a PKGBUILD; use makepkg.conf or env.
- **Python packaging**: Use `python -m build` + `python -m installer`, not
  `setup.py install`. See python-sse-starlette for the canonical pattern.

## Directory Layout

- Top-level packages: flat (`<pkgname>/PKGBUILD`)
- Grouped chains: `ia16-toolchain/`, `posix-compat-patches/`
- Automation: `scripts/` -- validate-all.sh, build-pkg.sh, submit-to-aur.sh
- CI: `.github/workflows/lint.yml`
- Docs: `docs/` -- CROSS_COMPILER_CHAINS.md, decisions/

## Common Pitfalls

1. **Duplicate depends=()**: bash silently overwrites the first assignment.
   Always use a single `depends=()` array (fixed in oterm/PKGBUILD).
2. **Trailing comma in source=()**: Makes the URL unparseable to makepkg
   (fixed in animatediffusion-git/PKGBUILD).
3. **PKGEXT inside PKGBUILD**: Non-standard; belongs in makepkg.conf.
4. **docker vs podman**: sonarqube-server uses podman throughout. Never
   reintroduce docker calls there.
5. **Cross-compiler build order**: Always binutils -> bootstrap gcc -> newlib
   -> full gcc. Using the chain Makefiles prevents ordering mistakes.

## Key Files

| File | Purpose |
|------|---------|
| `.gitignore` | Excludes build artifacts; .SRCINFO must NOT be excluded |
| `scripts/validate-all.sh` | Batch namcap + printsrcinfo check |
| `docs/CROSS_COMPILER_CHAINS.md` | Bootstrap chain dependency graphs |
| `CONTRIBUTING.md` | Guidelines for adding new packages |
