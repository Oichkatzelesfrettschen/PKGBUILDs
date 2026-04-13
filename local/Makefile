PKGBUILDS_ROOT := /home/eirikr/Github/pkgbuilds/local

.PHONY: smoke-limine-stack

smoke-limine-stack:
	@echo "[1/3] theme package smoke"
	@$(MAKE) -C "$(PKGBUILDS_ROOT)/cachyos-limine-themes" smoke
	@echo "[2/3] font package smoke"
	@$(MAKE) -C "$(PKGBUILDS_ROOT)/spline-cp437-limine-font" smoke
	@echo "[3/3] live limine verify"
	@sudo -A cachyos-limine-theme verify
	@echo "Full Limine stack smoke passed."
