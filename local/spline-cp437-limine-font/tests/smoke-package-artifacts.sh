#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

pkgver="$(awk -F= '/^pkgver=/{print $2}' PKGBUILD)"
pkgrel="$(awk -F= '/^pkgrel=/{print $2}' PKGBUILD)"
pkgfile="${repo_root}/spline-cp437-limine-font-${pkgver}-${pkgrel}-any.pkg.tar.zst"
listing="$(mktemp /tmp/spline-cp437-package-list.XXXXXX)"

cleanup() {
  rm -f "${listing}"
}
trap cleanup EXIT

echo "[1/3] build verification"
make test

echo "[2/3] package build"
makepkg --printsrcinfo > .SRCINFO
makepkg -f --nodeps --noprepare --nocheck
[[ -f "${pkgfile}" ]]

echo "[3/3] package content inspection"
bsdtar -tf "${pkgfile}" > "${listing}"
grep -qx 'usr/lib/spline-cp437-limine-font/build_limine_font.py' "${listing}"
grep -qx 'usr/lib/spline-cp437-limine-font/generate_cp437_report.py' "${listing}"
grep -qx 'usr/share/doc/spline-cp437-limine-font/README.md' "${listing}"
grep -qx 'usr/share/spline-cp437-limine-font/fonts/spline-cp437-8x16.bin' "${listing}"
grep -qx 'usr/share/spline-cp437-limine-font/fonts/spline-cp437-8x16.bdf' "${listing}"
grep -qx 'usr/share/spline-cp437-limine-font/fonts/spline-cp437-8x16.otb' "${listing}"
grep -qx 'usr/share/spline-cp437-limine-font/fonts/spline-cp437-sample.png' "${listing}"
grep -qx 'usr/share/spline-cp437-limine-font/fonts/spline-cp437-build.json' "${listing}"
grep -qx 'usr/share/spline-cp437-limine-font/reports/cp437-source-report.json' "${listing}"
grep -qx 'usr/share/spline-cp437-limine-font/reports/cp437-source-report.md' "${listing}"

echo "Smoke package artifacts passed."
