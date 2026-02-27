# ADR 002: Checksum Policy for PKGBUILD Sources

## Status: Accepted

## Context

Arch Linux PKGBUILDs support several checksum algorithms. The right checksum
to use (and when to use SKIP) depends on the source type and available
verification mechanism.

## Decision

| Source type | Checksum policy |
|-------------|-----------------|
| VCS sources (`git+`, `svn+`, etc.) | `SKIP` -- content defined by revision, not tarball |
| Local files in the PKGBUILD directory | Real sha256 via `updpkgsums` |
| Remote archives (PyPI, GitHub releases, SourceForge) | Real sha256 via `updpkgsums` |
| GPG-signed tarballs + `.sig` pairs | Real sha256 on tarball, `SKIP` on `.sig` |
| Stub/placeholder packages with no source | `sha256sums=()` (empty) |

Use sha256sums as the default algorithm. Never use md5sums (cryptographically
broken since 2004).

## Rationale

- sha256 provides cryptographic integrity for remote sources.
- VCS sources change with every commit; checksums are meaningless there.
- GPG `.sig` files are validated by the keyring, not by content hash.
- Defense-in-depth: even GPG-verified packages should have sha256 on the
  tarball to detect substitution attacks on the tarball before GPG runs.

## Process

Run `updpkgsums` in the package directory to compute and insert checksums.
This downloads sources if not cached. For large toolchain packages (GCC,
binutils), this is a prerequisite for AUR submission.

## Consequences

- `md5sums` removed from psp-sdk and gcc4ti (replaced with sha256sums).
- SKIP now only appears on VCS sources and `.sig` files.
- GCC-family packages document a reminder to run `updpkgsums` before AUR
  submission (tarballs are too large to download in CI).
