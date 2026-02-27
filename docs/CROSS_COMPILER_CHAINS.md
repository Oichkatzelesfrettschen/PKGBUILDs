# Cross-Compiler Toolchain Chains

This document describes the bootstrap build order for each cross-compiler
toolchain in this repository. Build order matters because GCC requires
binutils and a C library to be installed before the full compiler can be built.

## General Pattern

Most toolchains follow the same 4-step bootstrap sequence:

```
binutils -> gcc-stage1 (C only, no libc) -> newlib/libc -> gcc (full, C+C++)
```

The stage1 GCC is a minimal compiler (C only, `--without-headers` or
`--with-newlib`) used solely to compile the C library. Once the C library
exists, the full GCC can be built with C++ and libc support.

## Toolchain Inventory

### IA-16 (8086/186 real mode)

Target prefix: `ia16-elf`
Use case: 16-bit real mode x86, DOS/BIOS development
Build driver: `ia16-toolchain/Makefile`

```
binutils-ia16-custom
  -> gcc-ia16-custom-stage1  (C only)
     -> newlib-ia16-custom
        -> gcc-ia16-custom   (C + C++ + newlib)
           -> ia16-toolchain-meta  (meta-package)
```

### i386-elf

Target prefix: `i386-elf`
Use case: 32-bit protected mode, microkernel/OS development
Build driver: none (standalone packages; binutils from AUR)

```
i386-elf-binutils  (AUR or local)
  -> i386-elf-gcc  (C + C++)
```

Note: i386-elf-gcc includes MPFR/MPC/GMP as in-tree builds. Uses GPG
verification (`validpgpkeys`) for the GCC/MPFR/MPC/GMP tarballs.

### m68k-elf (Motorola 68000)

Target prefix: `m68k-elf`
Use case: Sega Genesis/Megadrive homebrew
Build driver: `Makefile.m68k`

```
m68k-elf-binutils  (AUR dependency)
  -> m68k-elf-gcc-bootstrap  (C only, --without-headers)
     -> m68k-elf-newlib
        -> m68k-elf-gcc      (C + C++, --with-cpu=m68000)
```

Note: Configured for `m68000` specifically. Multi-lib disabled. Remove
`--with-cpu=m68000` and enable `--enable-multilib` for other m68k variants.

### mips64-elf

Target prefix: `mips64-elf`
Use case: 64-bit MIPS bare metal
Build driver: `Makefile.mips64`

```
mips64-elf-binutils
  -> mips64-elf-gcc-stage1  (C only)
     -> mips64-elf-newlib
        -> mips64-elf-gcc   (C + C++)
```

### mips64el-linux-gnu (MIPS64 Linux userspace)

Target prefix: `mips64el-linux-gnu`
Use case: Cross-compilation targeting MIPS64 little-endian Linux
Build driver: none (standalone packages)

```
mips64el-linux-gnu-binutils
  -> mips64el-linux-gnu-linux-api-headers  (kernel headers)
     -> mips64el-linux-gnu-gcc-bootstrap   (C only, --without-headers)
```

Note: This is a partial chain; a full Linux userspace toolchain would also
need glibc and a stage2 GCC. The bootstrap GCC is the current endpoint.

### mipsel-elf

Target prefix: `mipsel-elf`
Use case: MIPS little-endian bare metal
Build driver: `Makefile.mipsel`

```
mipsel-elf-binutils
  -> mipsel-elf-gcc
```

### msp430-elf (TI MSP430 microcontrollers)

Target prefix: `msp430-elf`
Use case: TI MSP430 low-power microcontroller development
Build driver: `Makefile.msp430`

```
msp430-elf-binutils
  -> msp430-elf-gcc-stage1  (C only)
     -> msp430-elf-newlib
        -> msp430-elf-gcc   (C + C++)
           -> msp430-elf-mcu  (MCU headers and linker scripts)
```

### sh-elf (Hitachi SuperH)

Target prefix: `sh-elf`
Use case: SuperH RISC bare metal (SEGA Dreamcast, embedded systems)
Build driver: `Makefile.sh-elf`

```
sh-elf-binutils  (AUR dependency)
  -> sh-elf-newlib
     -> sh-elf-gcc
```

### PSP (PlayStation Portable)

Target prefix: `psp`
Use case: PSP homebrew development
Build driver: `Makefile.psp`

```
psp-binutils
  -> psp-gcc-base   (GCC for PSP target)
     -> psp-sdk     (PSPSDK - headers, libraries, tools)
```

Note: `psp-sdk` has `makedepends=('psp-gcc')` but the package is named
`psp-gcc-base`. Verify whether `psp-gcc-base` provides `psp-gcc` (see DD-01
in CONTRIBUTING.md). If not, install `psp-gcc` from AUR separately.

### PowerPC (Bleeding-edge toolchains)

These are pre-built toolchain packages, not source-built chains:

| Package | Target | Libc |
|---------|--------|------|
| `powerpc64-power8-musl-bleeding-edge-toolchain` | powerpc64-linux | musl |
| `powerpc64le-power8-glibc-bleeding-edge-toolchain` | powerpc64le-linux | glibc |
| `powerpc-440fp-glibc-bleeding-edge-toolchain` | powerpc-linux | glibc |

## Shared GCC Dependencies

All GCC source builds in this repo bundle MPFR, MPC, and GMP as in-tree
builds using symlinks in `prepare()`. This avoids host version conflicts:

```bash
ln -s ../mpfr-${_mpfrver}
ln -s ../mpc-${_mpcver}
ln -s ../gmp-${_gmpver}
```

All GCC tarballs are authenticated via `validpgpkeys` using GNU signing keys.
Run `updpkgsums` to add sha256 checksums as defense-in-depth before AUR submission.

## Notes on PKGEXT

Do not set `PKGEXT` inside PKGBUILDs. If you need a specific archive format
for a toolchain, set it in `~/.makepkg.conf` or pass it as an environment
variable:

```sh
PKGEXT='.pkg.tar.zst' makepkg -si
```
