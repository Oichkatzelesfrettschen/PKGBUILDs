---
target: https://aur.archlinux.org/packages/mate-menu
maintainer: NoOneExpects
---

**Subject: Panel icon resolution and pointer monitor fixes (pkgrel=5)**

Two independent bug fixes applied as a single patch. Both are observable regressions
on current GTK3 / Python-xlib versions.

---

**Fix 1: Dynamic panel icon resolution**

Problem: `mate-menu` hardcodes `self.icon = "start-here"` in `__init__`. On distributions
that ship a themed distributor logo (e.g. `distributor-logo-arch`,
`distributor-logo-ubuntu`) but not `start-here`, the panel button renders as a broken
image. The icon is also never re-evaluated when the theme changes.

Fix: add `resolve_panel_icon()` which reads `/etc/os-release` (`LOGO`, `ID`, `ID_LIKE`) and
probes `Gtk.IconTheme` and the filesystem (`/usr/share/icons`, `/usr/share/pixmaps`) for
the best available icon. Falls back through:

```
distributor-logo-<LOGO> -> distributor-logo-<ID> -> distributor-logo-<ID_LIKE[*]>
  -> distributor-logo -> start-here -> start-here-symbolic
```

Also: update `do_load_icon()` and `createAboutWindow()` to accept absolute file paths
(for distributions whose `LOGO` entry in os-release is a full path or SVG on disk)
using `GdkPixbuf.Pixbuf.new_from_file_at_scale`. Apply `load_surface` in a `try/except`
to handle icon theme lookup failures gracefully.

Call `resolve_panel_icon()` in `changeTheme()` and `reloadSettings()` so the icon updates
when the desktop theme changes.

---

**Fix 2: Pointer monitor race and crash**

Problem: `pointerMonitor.py` contains three bugs that cause crashes or missed events
under current python-xlib:

a) `self.running` is referenced in `run()` before being set in `activate()`, causing
   `AttributeError` if `run()` is called directly.

b) The pointer-inside check calls `self.get_window().get_device_position(pdevice)`.
   `self.get_window()` is a `Gtk.Window` method; `PointerMonitor` does not inherit from
   `Gtk.Window` and has no such method. This raises `AttributeError` every time a
   `ButtonPress` event arrives, silently swallowing the outside-click dismiss.

c) `display.allow_events()` is called inside the `except` block, so any exception in
   the button-press path causes the X server to block pointer events permanently
   until the grab is released externally.

Fix:

- Set `self.running = False` in `__init__` (safe default before `activate()`).
- Replace the broken Gdk device-position check with `_window_contains_pointer()`,
  which uses `window.get_origin()` and `window.get_width()`/`get_height()` directly
  on the Xlib `Window` object that was added via `addWindowToMonitor()`.
- Move `display.allow_events()` + `display.flush()` into a `finally:` block so X pointer
  events are always replayed regardless of exceptions in the event handler.

Patch file: `mate-menu-icon-and-pointer-fixes.patch`
(renamed from `mate-menu-cachyos-icon-and-pointer-fixes.patch` to be distro-neutral)

---

**Diff** (paste contents of `mate-menu.diff`):
