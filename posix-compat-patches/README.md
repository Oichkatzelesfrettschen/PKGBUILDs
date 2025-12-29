# POSIX Compatibility Patches for Arch Linux

Patches and PKGBUILDs for building POSIX/Plan9/suckless utilities on modern Arch Linux with GCC 14+ and glibc 2.34+.

## Packages

| Package | Version | Patches | Status |
|---------|---------|---------|--------|
| heirloom-sh | 050706-5 | GCC 14 signal handlers, SIGSTKSZ fix | Built & Validated |
| sbase-git | 0.1.r121.gc11a21f-2 | mkproto format fix | Built & Validated |
| ubase-git | 0.r616.ga570a80-1 | (depends on sbase-git) | Built & Validated |
| 9base-git | 20190913.117-2 | C99 `true` keyword conflicts | Built & Validated |

## Patches Created

### heirloom-sh
- `001-fix-gcc14-signal-handlers.patch`: Fixes GCC 14 pointer type errors and glibc 2.34 SIGSTKSZ constant
- `002-fix-gcc14-test-c.patch`: Fixes statf function pointer declaration

### sbase-git
- `001-fix-mkproto-format.patch`: Fixes proto file format bugs in mkproto script

### 9base-git
- `001-fix-c99-true-keyword.patch`: Renames `true` label/variable to avoid C99 stdbool.h conflicts
  - dd/dd.c: `true` label -> `match_found`
  - troff/n5.c: `true` variable -> `cond_result`

## Build Instructions

```bash
# Build individual package
cd <package-dir>
makepkg -f

# Install all packages
sudo pacman -U /home/eirikr/makepkg-output/packages/{heirloom-sh,sbase-git,ubase-git,9base-git}*.pkg.tar.zst
```

## AUR Submission

1. Add SSH key to AUR account:
   ```
   ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIN3NBXC6bD1dQkSDgPYZdz/7Vama1u4zI4C4uWl1zaes eirikr-aur
   ```

2. Clone and update AUR repos:
   ```bash
   cd aur-repos
   for pkg in heirloom-sh sbase-git ubase-git 9base-git; do
       git clone ssh://aur@aur.archlinux.org/$pkg.git
       cp -r ../$pkg/* $pkg/
       cd $pkg && git add -A && git commit -m "Update for GCC 14/glibc 2.34 compatibility" && git push
       cd ..
   done
   ```

## Technical Details

### GCC 14 Changes (2024)
- `-Wincompatible-pointer-types` is now an error by default
- `-Wimplicit-function-declaration` is now an error by default

### glibc 2.34+ Changes
- `SIGSTKSZ` is no longer a compile-time constant (varies for AVX-512)

### C99 Compliance
- `true`/`false` are reserved keywords via stdbool.h
- Plan 9 code predates C99 and uses `true` as identifiers
