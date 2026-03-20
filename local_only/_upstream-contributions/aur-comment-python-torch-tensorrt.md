---
target: https://aur.archlinux.org/packages/python-torch-tensorrt
maintainer: Smoolak
---

**Subject: Update to 2.10.0 + Python 3.14 (cp314) compatibility patches**

The AUR PKGBUILD is at 2.9.0-5 but pytorch/TensorRT 2.10.0 was released and
python-pytorch-opt-cuda in the cachyos repo is already at 2.10.0. The version
mismatch prevents import at runtime.

**Changes needed to build 2.10.0:**

- `pkgver=2.10.0` (source tarball SHA256: `08d1cb6de033a8fe7c5a9e8beda016af80319bcbc22c19c8e6044d01572df791`)
- bazel updated from 8.1.1 to 8.4.2 (required by `.bazelversion` in the 2.10.0 repo;
  8.1.1 refuses to run with a version mismatch error)
- `glog-0.7.patch` removed: the glog context changed in 2.10.0; injecting
  `-DGLOG_USE_GLOG_EXPORT` via `.bazelrc` is sufficient
- New `fix-prim-namespace.patch`: 2.10.0 declares `namespace prim {}` in a translation
  unit that also includes the libtorch header which uses
  `namespace prim = ::c10::prim` (an alias). Both in the same scope is a C++
  error. Fix: collapse the empty namespace block (cherry-picked from main branch).

**Python 3.14 (cp314) compatibility -- 4 new patches** for systems where the system
Python is 3.14 and TensorRT Python bindings are cp313-only:

**1. fix-py314-trt-stub.patch**
`_TensorRTProxyModule.py` currently calls `importlib.import_module("tensorrt")` and
if it raises `ImportError` installs a stub. Under cp314 the import does NOT raise
`ImportError` -- it returns a namespace package (any directory named `tensorrt/` on
`sys.path` is silently accepted). The proxy then crashes with `AttributeError` because
the namespace package has no `__version__`. Fix: validate `__version__` before
accepting the import, and if validation fails install a deep-proxy stub. The stub
uses `_TRTPlaceholderMeta` with a shared `_trt_cache` so that `trt.ITensor` and
`trt.tensorrt.ITensor` are the SAME class object -- required for
`enforce_tensor_types` identity checks. `__file__=None`, valid `ModuleSpec`,
`__path__=[]` prevent the import machinery from probing the stub as a real package.

**2. fix-py314-trt-logging.patch**
`_TRTLogger` inherits `trt.ILogger`. Under the stub, `trt.ILogger` is a placeholder
whose `__init__` raises `RuntimeError` by design. `TRT_LOGGER = _TRTLogger()` at
module level then crashes. Fix: wrap in `try/except ImportError/RuntimeError`.

**3. fix-py314-fx-converters.patch**
`trt.Logger()` and `trt.init_libnvinfer_plugins()` are called at module import time
inside an `if hasattr(trt, "__version__")` guard. The stub sets `__version__`
(intentionally, so version checks pass), so the block runs even under cp314.
Both calls raise `RuntimeError` via the stub. Fix: wrap in `try/except`.

**4. fix-py314-converter-registry.patch**
The FX legacy converter registry module imports `torch._dynamo` -> `sympy` -> `mpmath`.
Under cp314, version drift in sympy/mpmath can cause `ImportError` at that chain.
The dynamo frontend provides equivalent functionality. Fix: wrap in `try/except`.

**Wheel post-processing step** also required:
`python -m build --wheel` invokes `bazel build --config=python` which resolves
libtorch differently than `--compilation_mode=opt`. The `--config=python` path may
use cached nightly libtorch artifacts that are missing symbols from the system
`python-pytorch-opt-cuda` build, causing undefined symbol errors at runtime. Fix:
after the wheel is built, replace the three `libtorchtrt*.so` files inside the
wheel zip with the ones produced by the manual `bazel build //:libtorchtrt
--compilation_mode=opt` step (which was built against system torch via
`new_local_repository`). Update the RECORD SHA256 entries accordingly.

A cp314-specific build is published as
[python-torch-tensorrt-cp314](https://aur.archlinux.org/packages/python-torch-tensorrt-cp314)
if you prefer to keep this package targeting cp313 only.

The 4 cp314 patches are also suitable for upstream submission to pytorch/TensorRT.

---

**Diff** (paste contents of `python-torch-tensorrt.diff`):
