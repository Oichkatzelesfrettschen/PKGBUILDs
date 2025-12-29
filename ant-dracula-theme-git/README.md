# Ant-Dracula Theme (Patched for Modern Inkscape)

This is a patched AUR package build for the **Ant-Dracula** GTK theme.

## Fixes & Improvements

This version includes critical fixes for building with modern toolchains:

1.  **Inkscape 1.4+ Compatibility:** 
    - Replaced deprecated `-e` (export-png) and `-i` (export-id) flags with `--export-filename` and `--export-id`.
    - Removed reliance on the fragile `--shell` mode in Python scripts, switching to direct `subprocess` calls.
    - Fixes `InkscapeApplication::parse_actions: could not find action` errors during build.

2.  **Full Asset Generation:**
    - Explicitly enabled asset rendering for **GTK 4.0**, which was missing in previous versions (fixing `gtk_css_section_get_bytes` assertion crashes).
    - Ensures correct path navigation (`gtk-3.20/assets`, `gtk-4.0/assets`) so generated PNGs end up in the package, not lost in the source root.

3.  **Robust Error Handling:**
    - Added `set -e -o pipefail` to build steps.
    - Added verification steps to ensure PNG assets are actually created before packaging.

## Installation

```bash
git clone https://github.com/YourUsername/ant-dracula-theme-git.git
cd ant-dracula-theme-git
makepkg -si
```
