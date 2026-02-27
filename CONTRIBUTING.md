# Contributing

## Adding a New Package

1. Create a directory `<pkgname>/` at the repo root (or inside `ia16-toolchain/`
   or `posix-compat-patches/` if it belongs to one of those groups).

2. Write the `PKGBUILD` following these standards:

   - **Maintainer**: `# Maintainer: eirikr <eirikr@localhost>` for new packages.
     For packages sourced from AUR, keep the original maintainer and add
     `# Contributor: eirikr <eirikr@localhost>`.
   - **License**: Use SPDX identifiers (Arch RFC 0016). See `docs/decisions/002`.
   - **Checksums**: sha256sums for all non-VCS sources; SKIP only for VCS and
     `.sig` files. Run `updpkgsums` before committing. See `docs/decisions/002`.
   - **Python packages**: Use `python -m build` + `python -m installer`.
     See `docs/decisions/004`.
   - **PKGEXT**: Do not set inside PKGBUILDs. Use makepkg.conf.

3. Generate `.SRCINFO`:
   ```sh
   cd <pkgname>
   makepkg --printsrcinfo > .SRCINFO
   ```

4. Validate:
   ```sh
   sh scripts/validate-all.sh
   ```

5. Commit both `PKGBUILD` and `.SRCINFO` together.

## Checksum Policy

See `docs/decisions/002-checksum-policy.md` for the full policy.

Quick reference:
- VCS sources: `SKIP`
- Everything else: run `updpkgsums`
- Never use `md5sums`

## .SRCINFO Requirements

Every PKGBUILD directory must have a `.SRCINFO` file committed to git.
The `.gitignore` must NOT exclude `.SRCINFO`. If you see `.SRCINFO` in
`.gitignore`, remove that line immediately.

Regenerate all at once:
```sh
sh scripts/generate-all-srcinfo.sh
```

## Cross-Compiler Toolchains

New cross-compiler chains should:
1. Follow the bootstrap order documented in `docs/CROSS_COMPILER_CHAINS.md`.
2. Have a `Makefile.<target>` at the repo root to document and automate the
   build sequence.
3. Use `conflicts=` and `replaces=` to handle bootstrap vs. full packages.
4. For GCC-based toolchains, add `validpgpkeys` and include the MPFR/MPC/GMP
   version variables for in-tree builds.

## Python Packages

Follow `docs/decisions/004-python-packaging-standard.md`. Use
`python-sse-starlette/PKGBUILD` as the canonical reference for a well-formed
Python PKGBUILD with modern build system, check(), and proper makedepends.

## Known Issues (DD = Dependency Debt)

- **DD-01**: `psp-sdk` has `makedepends=('psp-gcc')` but the package is named
  `psp-gcc-base`. Fixed by adding `provides=('psp-gcc')` to `psp-gcc-base`.
- **DD-02**: `oterm` depends on `python-fastmcp` and `python-mcp` which are
  AUR-only packages. Install them with `yay` before building.

## Submitting to AUR

Use the automation script:
```sh
sh scripts/submit-to-aur.sh <package-dir> --dry-run  # preview
sh scripts/submit-to-aur.sh <package-dir>             # submit
```

This requires an SSH key registered at https://aur.archlinux.org/account/
