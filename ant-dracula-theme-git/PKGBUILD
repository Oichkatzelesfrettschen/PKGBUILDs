# Maintainer: Tony Lambiris <tony@libpcap.net>

pkgname=ant-dracula-theme-git
_pkgname=Ant-Dracula
pkgver=4.0.0.r137.gfccbc2e
pkgrel=1
pkgdesc="Dracula variant of the Ant theme"
arch=("any")
url="https://github.com/EliverLara/${_pkgname}"
license=('GPL')
depends=('gtk-engine-murrine')
makedepends=('git' 'inkscape' 'optipng')
optdepends=('gtk-engines: for GTK2 pixmap engine'
			'ttf-roboto: primary font face defined'
			'ttf-ubuntu-font-family: secondary font face defined'
			'cantarell-fonts: tertiary font face defined')
conflicts=('ant-dracula-gtk-theme')
provides=('ant-dracula-gtk-theme')
source=("${_pkgname}::git+https://github.com/EliverLara/${_pkgname}.git")
sha256sums=('SKIP')

prepare() {
	set -e -o pipefail
  	cd "${srcdir}/${_pkgname}"

	msg2 "Patching rendering scripts for modern Inkscape compatibility..."
	# Patch standard rendering scripts
	find . -name "*.py" ! -name "*-hidpi.py" -exec sed -i '/def inkscape_render_rect/,/optimize_png(output_file)/c\def inkscape_render_rect(icon_file, rect, output_file):\n    subprocess.run([INKSCAPE, "--export-id=" + rect, "--export-id-only", "--export-background-opacity=0", "--export-filename=" + output_file, icon_file], check=True)\n    optimize_png(output_file)' {} +
	# Patch HiDPI rendering scripts
	find . -name "*-hidpi.py" -exec sed -i '/def inkscape_render_rect/,/optimize_png(output_file)/c\def inkscape_render_rect(icon_file, rect, output_file):\n    subprocess.run([INKSCAPE, "--export-dpi=180", "--export-id=" + rect, "--export-id-only", "--export-background-opacity=0", "--export-filename=" + output_file, icon_file], check=True)\n    optimize_png(output_file)' {} +
}

pkgver() {
  	cd "${srcdir}/${_pkgname}"

	git describe --long --tags | sed 's/\([^-]*-g\)/r\1/;s/-/./g;s/^v//g'
}

build() {
	set -e -o pipefail
  	cd "${srcdir}/${_pkgname}"

	export THEME_FONT_FACE="${THEME_FONT_FACE:-Roboto}"
	export THEME_FONT_SIZE="${THEME_FONT_SIZE:-10}"

	msg2 "To customize the font and size for gnome-shell, build this package"
	msg2 "with the variables below set to the desired font family and size"
	msg2 "- THEME_FONT_FACE (default font family is Roboto)"
	msg2 "- THEME_FONT_SIZE (default font point size is 10)"
	msg2 ""
	msg2 "Continuing build in 5 seconds..."; sleep 5

	msg2 "Rendering GTK2 assets..."
	cd gtk-2.0
	./render-assets.sh
	cd ..

	msg2 "Rendering GTK 3.20 assets..."
	cd gtk-3.20/assets
	./render-gtk3-assets.py
	./render-gtk3-assets-hidpi.py
	cd ../..

	msg2 "Rendering GTK 4.0 assets..."
	cd gtk-4.0/assets
	./render-gtk3-assets.py
	./render-gtk3-assets-hidpi.py
	cd ../..

	msg2 "Rendering WM assets..."
	cd src
	./render-wm-assets.py
	./render-wm-assets-hidpi.py
	cd ..
	
	msg2 "Verifying asset generation..."
	if [ ! -d "assets" ] || [ -z "$(ls -A assets/*.png 2>/dev/null)" ]; then
		error "No PNG assets were generated in the assets/ directory! Rendering failed."
		exit 1
	fi
	msg2 "Assets rendered and verified successfully!"

	msg2 "Setting gnome-shell font face to ${THEME_FONT_FACE}"
	msg2 "Setting gnome-shell font size to ${THEME_FONT_SIZE}"

	if [ "${THEME_FONT_FACE}" != "Roboto" ]; then
		sed -i -re "s/font-family: (.*);/font-family: ${THEME_FONT_FACE}, \1;/" \
			"${srcdir}/${_pkgname}/gnome-shell/gnome-shell.css"
	fi

	if [ "${THEME_FONT_SIZE}" != "10" ]; then
		sed -i -re "s/font-size: (.*);/font-size: ${THEME_FONT_SIZE}pt;/" \
			"${srcdir}/${_pkgname}/gnome-shell/gnome-shell.css"
	fi
}

package() {
  	cd "${srcdir}/${_pkgname}"

	mkdir -p "${pkgdir}/usr/share/themes/${_pkgname}"
	cp -a "${srcdir}/${_pkgname}/"* "${pkgdir}/usr/share/themes/${_pkgname}/"
}
