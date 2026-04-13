# cachyos-limine-themes

CachyOS-oriented Limine visual themes with TrueColor wallpapers from the
official CachyOS wallpapers repository, scaled bitmap fonts for 4K
readability, and a package-managed boot workflow.

## Available themes

| Theme    | Wallpaper               | Description                              |
|----------|-------------------------|------------------------------------------|
| galaxy   | cachygalaxy99.jpg       | Dark blue/teal waves (flagship, default) |
| north    | north.png               | Moonlit ocean with CachyOS logo          |
| depths   | Cachy depths 5K.png     | Deep teal gradient with CachyOS logo     |

All themes use `term_font_scale: 2x2` for readable text at native 4K
resolution with the 8x16 Spline CP437 bitmap font (effective 16x32).

## Display policy

- Themes do not set `interface_resolution`.
- Per the Limine manual, when `interface_resolution` is omitted, Limine picks
  a supported mode automatically.
- This is the safest default across displays from legacy `800x600` panels up
  through modern `4K` and ultrawide displays.

## What this package ships

- Theme config snippets under `/usr/share/cachyos-limine-themes/themes/`
- TrueColor wallpapers under `/usr/share/cachyos-limine-themes/wallpapers/`
- A helper under `/usr/bin/cachyos-limine-theme`

Wallpapers are downloaded from the official CachyOS wallpapers repo during
build and bundled in the package. No runtime dependency on
`cachyos-wallpapers`.

## Normal workflow

```bash
<your favorite pacman-compatible installer> cachyos-limine-themes
```

The default theme (`galaxy`) is applied automatically during install.

To switch themes:

```bash
sudo -A cachyos-limine-theme apply north
```

## Staging

Limine reads from the boot partition, not from `/usr/share`. This package
stages the chosen wallpaper and font into:

`/boot/limine/themes/cachyos-official/`

The helper supports:

- `list` to show available themes
- `show <theme>` to print the packaged theme snippet
- `render <theme>` to print the exact managed block
- `status` to report current staging/apply state
- `verify` to validate staged assets, config structure, and `boot():` paths
- `apply <theme>` to stage and apply a theme
- `rollback` to restore the last backup recorded by the helper

## Rollback

Uninstalling the package triggers an automatic rollback. For manual recovery:

```bash
sudo -A cachyos-limine-theme rollback
```

Package uninstall restores the original pre-theme config that existed before
the first package-managed apply.

## Verification

```bash
sudo -A cachyos-limine-theme verify
```

## Local smoke test

```bash
cd ~/Github/pkgbuilds/local/cachyos-limine-themes
make smoke
```
