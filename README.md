# pkgbuilds

A collection of Arch Linux PKGBUILDs for cross-compiler toolchains, Python
ecosystem packages, development tools, system configuration, and POSIX
compatibility patches.

## Repository Layout

```
pkgbuilds/
  <package-name>/         Top-level packages (flat layout)
    PKGBUILD
    .SRCINFO
  ia16-toolchain/         IA-16 toolchain sub-packages (grouped)
    binutils-ia16-custom/
    gcc-ia16-custom-stage1/
    newlib-ia16-custom/
    gcc-ia16-custom/
    ia16-toolchain-meta/
    Makefile
  posix-compat-patches/   POSIX compatibility tools (grouped)
    heirloom-sh/
    9base-git/
    ubase-git/
    sbase-git/
    install-all.sh
    submit-to-aur.sh
  scripts/                Build and maintenance automation
  docs/                   Architecture and decision records
  Makefile.m68k           m68k-elf toolchain build driver
  Makefile.mips64         mips64-elf toolchain build driver
  Makefile.mipsel         mipsel-elf toolchain build driver
  Makefile.msp430         msp430-elf toolchain build driver
  Makefile.psp            PSP toolchain build driver
  Makefile.sh-elf         sh-elf toolchain build driver
```

Packages are flat by default (directory name = pkgname). The exceptions are:
- `ia16-toolchain/` and `posix-compat-patches/`: multi-package groups with a
  shared build driver or install script.
- `libmateweather-radar-fix/`: directory name describes the patch, pkgname is
  `libmateweather`. See `libmateweather-radar-fix/README.md` for rationale.

## Package Categories

| Category | Packages | Notes |
|----------|----------|-------|
| Cross-compiler toolchains | ~38 | See docs/CROSS_COMPILER_CHAINS.md |
| Python packages | 9 | pdfplumber, pillow6, mkl, pypdfium2, sse-starlette, asgi-lifespan, backports-zstd, mcp (via oterm) |
| Development tools | infer-static, sonarqube-server, tla-plus-toolbox, mathcomp | Static analysis and formal methods |
| System config | eirikr-system-optimizations, ai-cli-memory-guards | Workstation tuning |
| UI themes | ant-dracula-theme-git, dracula-unified-theme-meta, picom-custom-git, libmateweather-radar-fix | Desktop appearance |
| POSIX compat | heirloom-sh, 9base-git, ubase-git, sbase-git | Portable POSIX utilities |
| Misc | yay, qmk, mozwire-git, gbdk-2020, cmoc, wmweather+, oterm | Various |

## Building Packages

### Single package

```sh
cd <package-dir>
makepkg -si
```

Or use the wrapper script for consistent output directories and post-build namcap:

```sh
sh scripts/build-pkg.sh <package-dir>
```

### Cross-compiler toolchains

Each toolchain has a dedicated Makefile that enforces the correct build order:

```sh
# m68k-elf (Genesis/Megadrive)
make -f Makefile.m68k all

# msp430-elf (TI microcontrollers)
make -f Makefile.msp430 all

# IA-16 (8086/186 real mode)
cd ia16-toolchain && make all
```

See `docs/CROSS_COMPILER_CHAINS.md` for dependency graphs and rationale.

## Validation

```sh
# Lint all PKGBUILDs (namcap + printsrcinfo)
sh scripts/validate-all.sh

# Generate missing .SRCINFO files
sh scripts/validate-all.sh --fix-srcinfo

# Check shell scripts
shellcheck -S error scripts/*.sh posix-compat-patches/*.sh sonarqube-server/*.sh
```

## Checksum Policy

| Source type | Checksum |
|-------------|----------|
| VCS (`git+`, `svn+`, etc.) | SKIP (content changes with commits) |
| Local files in the PKGBUILD directory | Real sha256 (run `updpkgsums`) |
| Remote archives | Real sha256 (run `updpkgsums`) |
| GPG-signed tarballs | Real sha256 on tarball + SKIP on `.sig` |

## Maintenance Cadence

- **Monthly**: Run `sh scripts/check-updates.sh` to find outdated package versions.
- **Quarterly**: Regenerate all `.SRCINFO` files with `sh scripts/validate-all.sh --fix-srcinfo`.
- **Annually**: Audit license identifiers for SPDX compliance (Arch RFC 0016).

## License

The PKGBUILDs themselves are released under GPL-3.0 (see `LICENSE`). Each
packaged software has its own upstream license as declared in the `license=`
array of each PKGBUILD.
