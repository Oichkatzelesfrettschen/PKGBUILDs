#!/bin/sh
set -eu

case "${XDG_CURRENT_DESKTOP:-}" in
  *MATE*) ;;
  *) exit 0 ;;
esac

current_version=$(
  pacman -Q mate-spline-font-defaults 2>/dev/null | awk '{print $2}'
)

[ -n "$current_version" ] || exit 0

state_root="${XDG_STATE_HOME:-$HOME/.local/state}/mate-spline-font-defaults"
state_file="$state_root/applied-version"

if [ -r "$state_file" ] && [ "$(cat "$state_file")" = "$current_version" ]; then
  exit 0
fi

if gsettings writable org.mate.interface font-name >/dev/null 2>&1; then
  gsettings set org.mate.interface font-name 'Spline Sans 11'
  gsettings set org.mate.interface document-font-name 'Spline Sans 11'
  gsettings set org.mate.interface monospace-font-name 'Spline Sans Mono 11'
fi

if gsettings writable org.mate.Marco.general titlebar-font >/dev/null 2>&1; then
  gsettings set org.mate.Marco.general titlebar-uses-system-font false
  gsettings set org.mate.Marco.general titlebar-font 'Spline Sans Bold 11'
fi

if gsettings writable org.mate.caja.desktop font >/dev/null 2>&1; then
  gsettings set org.mate.caja.desktop font 'Spline Sans Bold 11'
fi

if gsettings writable org.mate.pluma editor-font >/dev/null 2>&1; then
  gsettings set org.mate.pluma use-default-font false
  gsettings set org.mate.pluma editor-font 'Spline Sans Mono 11'
fi

if gsettings writable org.mate.terminal.profile:/org/mate/terminal/profiles/default/ font >/dev/null 2>&1; then
  gsettings set org.mate.terminal.profile:/org/mate/terminal/profiles/default/ use-system-font false
  gsettings set org.mate.terminal.profile:/org/mate/terminal/profiles/default/ font 'Spline Sans Mono 11'
fi

mkdir -p "$state_root"
printf '%s\n' "$current_version" > "$state_file"
