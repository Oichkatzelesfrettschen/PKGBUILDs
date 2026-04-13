#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
helper="${repo_root}/cachyos-limine-theme"
install_script="${repo_root}/cachyos-limine-themes.install"
fake_root="$(mktemp -d /tmp/cachyos-limine-smoke.XXXXXX)"
boot_dir="${fake_root}/boot"
config_path="${boot_dir}/limine.conf"

cleanup() {
  rm -rf "${fake_root}"
}
trap cleanup EXIT

mkdir -p \
  "${boot_dir}/EFI/tools" \
  "${boot_dir}/limine" \
  "${boot_dir}"

cat > "${config_path}" <<'EOF'
timeout: 5

/CachyOS
    protocol: linux
    path: boot():/vmlinuz-linux-cachyos
    cmdline: quiet splash
    module_path: boot():/initramfs-linux-cachyos.img

/CachyOS Fallback
    protocol: linux
    path: boot():/vmlinuz-linux-cachyos
    cmdline: quiet splash
    module_path: boot():/initramfs-linux-cachyos-fallback.img

/UEFI Shell
    protocol: efi
    path: boot():/EFI/tools/shellx64.efi
EOF
touch \
  "${boot_dir}/vmlinuz-linux-cachyos" \
  "${boot_dir}/initramfs-linux-cachyos.img" \
  "${boot_dir}/initramfs-linux-cachyos-fallback.img" \
  "${boot_dir}/EFI/tools/shellx64.efi"

original_hash="$(sha256sum "${config_path}" | awk '{print $1}')"

export THEME_HELPER="${helper}"
export THEME_NAME="galaxy"
export BOOT_DIR="${boot_dir}"
export CONFIG_PATH="${config_path}"

# shellcheck disable=SC1090
source "${install_script}"

echo "[1/4] post_install"
post_install
post_install_hash="$(sha256sum "${config_path}" | awk '{print $1}')"
[[ "${post_install_hash}" != "${original_hash}" ]]
grep -qx '# BEGIN CACHYOS-LIMINE-THEME' "${config_path}"
[[ -f "${boot_dir}/limine/themes/cachyos-official/cachygalaxy99.jpg" ]]
[[ -f "${boot_dir}/limine/themes/cachyos-official/fonts/spline-cp437-8x16.bin" ]]
[[ -f "${boot_dir}/limine/themes/cachyos-official/.state.env" ]]

echo "[2/4] helper verify"
bash "${helper}" verify --boot-dir "${boot_dir}" --config "${config_path}" >/tmp/cachyos-limine-smoke.verify
grep -q '^verify_result=ok$' /tmp/cachyos-limine-smoke.verify

echo "[3/4] post_upgrade"
sleep 1
post_upgrade
post_upgrade_hash="$(sha256sum "${config_path}" | awk '{print $1}')"
[[ -n "${post_upgrade_hash}" ]]
grep -qx '# BEGIN CACHYOS-LIMINE-THEME' "${config_path}"

echo "[4/4] pre_remove"
pre_remove
rollback_hash="$(sha256sum "${config_path}" | awk '{print $1}')"
[[ "${rollback_hash}" == "${original_hash}" ]]
[[ ! -d "${boot_dir}/limine/themes/cachyos-official" ]]

echo "Smoke lifecycle passed."
