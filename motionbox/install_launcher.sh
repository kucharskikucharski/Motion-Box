#!/usr/bin/env bash
# Adds "Motion Box" to your applications menu (and the Desktop) so you can start it with a click.
# Run ./run_mac_linux.sh once from a terminal first (it installs pygame on the first start).
DIR="$(cd "$(dirname "$0")" && pwd)"
APPS="$HOME/.local/share/applications"
mkdir -p "$APPS"
cat > "$APPS/motionbox.desktop" <<EOT
[Desktop Entry]
Type=Application
Name=Motion Box
Comment=2D animation software
Exec=bash -c 'cd "$DIR" && ./run_mac_linux.sh'
Icon=$DIR/assets/icon.png
Terminal=false
Categories=Graphics;
EOT
chmod +x "$APPS/motionbox.desktop"
if [ -d "$HOME/Desktop" ]; then
  cp "$APPS/motionbox.desktop" "$HOME/Desktop/"
  chmod +x "$HOME/Desktop/motionbox.desktop"
  gio set "$HOME/Desktop/motionbox.desktop" metadata::trusted true 2>/dev/null
fi
update-desktop-database "$APPS" 2>/dev/null
echo "Done - look for 'Motion Box' in your applications menu (and on the Desktop)."
