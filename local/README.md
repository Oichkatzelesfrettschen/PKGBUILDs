# Local PKGBUILD Stack

This directory contains local package trees and smoke harnesses for package work
that is not part of the main `open_gororoba` repo.

## Limine stack smoke

For the Limine theme plus companion font stack, run:

```bash
cd ~/Github/pkgbuilds/local
make smoke-limine-stack
```

That orchestrates:

- the fake-boot lifecycle smoke test for `cachyos-limine-themes`
- the packaged-artifact smoke test for `spline-cp437-limine-font`
- a final live `sudo -A cachyos-limine-theme verify`
