gcc13-sidecar-bin
=================

Purpose
-------

This package installs archived Arch Linux gcc13 and gcc13-libs binaries as a
secondary host toolchain. It is meant to coexist with newer system GCC
releases and be selected explicitly when older CUDA or NVHPC-sidecar toolchains
need an older host compiler.

Files
-----

- `/usr/bin/gcc-13`
- `/usr/bin/g++-13`
- `/usr/lib/gcc/x86_64-pc-linux-gnu/13.3.0/...`
- `/opt/gcc13-sidecar/gcc13-sidecar.sh`

Usage
-----

```sh
source /opt/gcc13-sidecar/gcc13-sidecar.sh
```

Then pass `-ccbin /usr/bin/g++-13` to `nvcc` when needed.
