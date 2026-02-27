# ADR 004: Python Packaging Standard

## Status: Accepted

## Context

Python packaging has evolved significantly. Older PKGBUILDs used `setup.py
install` which is deprecated and removed in Python 3.12+. Several packages
in this repository inherited the old pattern.

## Decision

All Python packages in this repository use the modern PEP 517 build frontend:

```bash
build() {
  cd "$_name-$pkgver"
  python -m build --wheel --no-isolation
}

package() {
  cd "$_name-$pkgver"
  python -m installer --destdir="$pkgdir" dist/*.whl
}
```

## Rationale

- `python -m build` invokes the build backend declared in `pyproject.toml`
  (or falls back to setuptools). It is the standard PEP 517 frontend.
- `python -m installer` installs the wheel into the package directory using
  INSTALLER metadata, which pacman can track correctly.
- `setup.py install` bypasses PEP 517, does not produce a wheel, and has
  been removed from setuptools >= 59.0 for many package types.
- `pip install --root=` works but creates untracked files and bypasses pacman
  metadata. `python -m installer` is the correct pacman-compatible approach.

## makedepends

```
makedepends=('python-build' 'python-installer' 'python-wheel' 'python-setuptools')
```

Add `python-pdm-backend`, `python-flit-core`, etc. as needed for packages
using those build backends.

## Affected Packages

- `python-pdfplumber`: migrated from `setup.py build/install`
- `python-asgi-lifespan`: migrated from `setup.py build/install`; also fixed
  `package_python-asgi-lifespan()` split-function name to `package()`
- `python-mkl`: migrated from `pip install --root=` to `python -m installer`
