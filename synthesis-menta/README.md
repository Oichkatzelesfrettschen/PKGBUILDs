# SynthesisMenta PKGBUILD Family

This package family breaks the theme suite into one PKGBUILD per backend or
domain surface instead of using one large split PKGBUILD.

## Source of Truth

- Upstream source repo:
  `https://github.com/Oichkatzelesfrettschen/Synthesis-Dark-Theme`
- Current pinned upstream commit:
  `a0b5e966`

Each package pulls from the canonical theme repo and uses the granular
`install-*` targets exposed by that repo's `Makefile`.

## Package Matrix

- `synthesis-menta-gtk-theme`
- `synthesis-menta-gnome-shell-theme`
- `synthesis-menta-cinnamon-theme`
- `synthesis-menta-xfwm4-theme`
- `synthesis-menta-unity-theme`
- `synthesis-menta-marco-theme`
- `synthesis-menta-icons`
- `synthesis-menta-icons-variants`
- `synthesis-menta-cursors`
- `synthesis-menta-wallpapers`
- `synthesis-menta-tilix`
- `synthesis-menta-pluma`
- `synthesis-menta-mate-terminal`
- `synthesis-menta-kde-colors`
- `synthesis-menta-kde-aurorae`
- `synthesis-menta-kde-plasma`
- `synthesis-menta-kde-sddm`
- `synthesis-menta-kvantum`
- `synthesis-menta-suite`

## Maintenance

Regenerate `.SRCINFO` files after any PKGBUILD change:

```sh
make -C synthesis-menta srcinfo
```
