# libmateweather-radar-fix

This directory is named `libmateweather-radar-fix` to describe the local patch
it contains (disabling a deprecated weather.com radar URL), but the PKGBUILD
produces a package named `libmateweather` (pkgname=libmateweather).

The naming deviation from the Arch convention (directory = pkgname) is
intentional here to make the patch purpose self-documenting at a glance.
See `docs/decisions/003-cross-compiler-prefix-convention.md` for the full
naming rationale.

## What the patch does

The upstream `libmateweather` package includes a weather.com radar feature
that points to a deprecated/removed URL, causing the radar widget to fail.
This PKGBUILD applies a local patch to disable that radar functionality and
keep the rest of the package functional.
