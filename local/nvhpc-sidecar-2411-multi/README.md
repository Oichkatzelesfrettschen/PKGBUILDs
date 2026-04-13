# nvhpc-sidecar-2411-multi

This package installs the NVIDIA HPC SDK 24.11 multi-toolkit bundle as a
sidecar for toolchain research. It is designed to support side-by-side PTXAS
and CUDA subtree sweeps without disturbing the system default CUDA install.

## Goals

- keep `/opt/cuda` as the primary CUDA 13.x toolchain
- install archived NVIDIA HPC SDK under a non-conflicting prefix
- make CUDA 11.8 and 12.6 toolchains opt-in rather than global
- support `ptxas` and frontend sweeps for the `P2R.B*` frontier

## Install prefix

- `/opt/nvidia/hpc_sdk_sidecar`

## Opt-in environment helpers

- `/opt/nvidia/nvhpc-sidecar.sh`
- `/opt/nvidia/nvhpc-sidecar-cuda11.8.sh`
- `/opt/nvidia/nvhpc-sidecar-cuda12.6.sh`

## Usage

Keep the system default CUDA:

```bash
nvcc --version
ptxas --version
```

Enable the sidecar compilers only:

```bash
source /opt/nvidia/nvhpc-sidecar.sh
```

Enable the archived CUDA 11.8 subtree for a real older `ptxas` sweep:

```bash
source /opt/nvidia/nvhpc-sidecar-cuda11.8.sh
ptxas --version
```

Enable the sidecar CUDA 12.6 subtree:

```bash
source /opt/nvidia/nvhpc-sidecar-cuda12.6.sh
ptxas --version
```

## Notes

- This package intentionally does not conflict with the current `cuda`
  package.
- `localrc` is generated against the system `gcc` by default.
- Override the compiler used for `makelocalrc` by exporting
  `NVHPC_LOCALRC_GCC=/path/to/gcc-wrapper-or-name` before building.
