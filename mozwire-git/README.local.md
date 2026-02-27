# `mozwire-git`: clang + LTO build notes (local)

## Why this exists

This system uses aggressive global `/etc/makepkg.conf` flags, including `OPTIONS=(... lto ...)` and GCC-oriented `CFLAGS`/`LTOFLAGS`.

`mozwire` depends on the Rust crate `ring`, which compiles C/asm via the `cc` crate and inherits `CFLAGS`. If those `CFLAGS` include GCC LTO flags (e.g. `-flto=auto -fno-fat-lto-objects`), the produced objects contain `.gnu.lto_*` sections. When the final Rust link uses `lld` (common with modern Rust toolchains), `lld` can’t consume GCC LTO “slim” objects, and the link fails with missing `ring_core_*` symbols.

## What we do here

The `PKGBUILD` forces a clang-based toolchain for this package build:

- `CC=clang`, `CXX=clang++`
- `CFLAGS`/`CXXFLAGS` replaced with a clang-friendly set including `-flto=thin`
- `LDFLAGS` uses `-fuse-ld=lld`
- `RUSTFLAGS` uses `-C linker=clang -C link-arg=-fuse-ld=lld` (don’t force `-C lto` via `RUSTFLAGS`, it conflicts with Cargo’s `-C embed-bitcode=no` for build scripts)

This keeps LTO enabled, but makes it compatible end-to-end.

## How to build

- `cd ~/.cache/yay/mozwire-git`
- `makepkg -s`

The resulting package lands in `PKGDEST` (configured in `/etc/makepkg.conf`), typically:

- `/home/eirikr/makepkg-output/packages/`

## Alternative: one-off session override (no PKGBUILD edits)

You can also do a one-off build by setting env vars on the command line, e.g.:

- `env CC=clang CXX=clang++ AR=llvm-ar NM=llvm-nm RANLIB=llvm-ranlib STRIP=llvm-strip CFLAGS='-O3 -pipe -march=znver3 -mtune=znver3 -flto=thin' CXXFLAGS='-O3 -pipe -march=znver3 -mtune=znver3 -flto=thin' LDFLAGS='-Wl,-O1 -Wl,--as-needed -fuse-ld=lld' RUSTFLAGS='-C opt-level=3 -C target-cpu=znver3 -C codegen-units=1 -C linker=clang -C link-arg=-fuse-ld=lld -C lto=thin' makepkg -s`
- `env CC=clang CXX=clang++ AR=llvm-ar NM=llvm-nm RANLIB=llvm-ranlib STRIP=llvm-strip CFLAGS='-O3 -pipe -march=znver3 -mtune=znver3 -flto=thin' CXXFLAGS='-O3 -pipe -march=znver3 -mtune=znver3 -flto=thin' LDFLAGS='-Wl,-O1 -Wl,--as-needed -fuse-ld=lld' RUSTFLAGS='-C opt-level=3 -C target-cpu=znver3 -C codegen-units=1 -C linker=clang -C link-arg=-fuse-ld=lld' makepkg -s`

## Verified (2026-01-19)

- Built successfully from `~/pkgbuilds/mozwire-git` with `BUILDDIR=$(mktemp -d -p /tmp makepkg-mozwire.final.XXXXXX)` and `makepkg -s -f`.
  - Note: `makepkg` warned about failing to update the cached VCS repo from GitHub (`Failed to connect to github.com:443`). The build still worked because `SRCDEST=/home/eirikr/makepkg-output/sources` already contained a usable clone at `/home/eirikr/makepkg-output/sources/mozwire` with `HEAD=b680ad2…`, so `makepkg` could create the working copy from the cached repo even without fetching.
  - If you need to ensure you’re building the latest upstream commit, rerun when connectivity is back or manually `git -C /home/eirikr/makepkg-output/sources/mozwire fetch --all --prune`.
- Package produced: `/home/eirikr/makepkg-output/packages/mozwire-git-0.8.1.r9.gb680ad2-1-x86_64.pkg.tar.zst`.
- Installed successfully via `sudo pacman -U --noconfirm /home/eirikr/makepkg-output/packages/mozwire-git-0.8.1.r9.gb680ad2-1-x86_64.pkg.tar.zst`.
- Smoke tests:
  - `mozwire --version` prints `mozwire 0.8.1`.
  - `mozwire --help`, `mozwire help relay`, `mozwire help device` work.
  - Tokened/API flows were not exercised (would require Mozilla auth).
