#!/usr/bin/env bash
set -euo pipefail

source /opt/nvidia/nvhpc-sidecar.sh

nvhome=/opt/nvidia/hpc_sdk_sidecar
target=Linux_x86_64
version=24.11
nvcudadir=$nvhome/$target/$version/cuda/11.8

export NVHPC_DEFAULT_CUDA=11.8
export CUDA_HOME=$nvcudadir
export CUDACXX=$nvcudadir/bin/nvcc
export PATH=$nvcudadir/bin:$PATH
export LD_LIBRARY_PATH=$nvcudadir/lib64:${LD_LIBRARY_PATH:-}
export LD_LIBRARY_PATH=$nvcudadir/extras/CUPTI/lib64:$LD_LIBRARY_PATH

echo "NVHPC sidecar CUDA 11.8 enabled from $nvcudadir"
