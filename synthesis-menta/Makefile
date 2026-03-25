PACKAGES = \
	synthesis-menta-gtk-theme \
	synthesis-menta-gnome-shell-theme \
	synthesis-menta-cinnamon-theme \
	synthesis-menta-xfwm4-theme \
	synthesis-menta-unity-theme \
	synthesis-menta-marco-theme \
	synthesis-menta-icons \
	synthesis-menta-icons-variants \
	synthesis-menta-cursors \
	synthesis-menta-wallpapers \
	synthesis-menta-tilix \
	synthesis-menta-pluma \
	synthesis-menta-mate-terminal \
	synthesis-menta-kde-colors \
	synthesis-menta-kde-aurorae \
	synthesis-menta-kde-plasma \
	synthesis-menta-kde-sddm \
	synthesis-menta-kvantum \
	synthesis-menta-suite

.PHONY: srcinfo

srcinfo:
	@for pkg in $(PACKAGES); do \
		echo "==> $$pkg"; \
		( cd "$$pkg" && makepkg --printsrcinfo > .SRCINFO ); \
	done
