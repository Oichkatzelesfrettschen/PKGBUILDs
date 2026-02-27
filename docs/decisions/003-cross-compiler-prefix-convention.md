# ADR 003: Cross-Compiler Package Naming Convention

## Status: Accepted

## Context

Cross-compiler toolchain packages need a consistent naming convention that
identifies the target triple, avoids conflicts with host compiler packages,
and matches Arch Linux packaging conventions.

## Decision

Package names follow the pattern `<target-triple>-<component>`:

- `<target-triple>` is the GCC/binutils target triple (e.g. `m68k-elf`,
  `msp430-elf`, `i386-elf`, `ia16-elf`)
- `<component>` is one of: `binutils`, `gcc`, `gcc-bootstrap`, `gcc-stage1`,
  `newlib`, `mcu`, `sdk`

Bootstrap/stage packages are separate from the final package and conflict with
it via the `conflicts=()` array.

## Rationale

- Matches existing AUR naming for cross-compiler packages.
- The target triple makes the architecture and ABI immediately visible.
- Separate bootstrap packages allow building the toolchain in a clean
  environment without the full compiler installed.

## Package Directory Naming

Package directories use the package name (e.g. `m68k-elf-gcc/`). The
exception is `ia16-toolchain/` which groups all ia16 sub-packages due to the
complexity of the chain and the shared Makefile.

The `libmateweather-radar-fix/` directory is named for the patch purpose
rather than the pkgname (`libmateweather`). This is documented here as a
known deviation -- the directory should ideally be renamed to `libmateweather/`
in a future cleanup.
