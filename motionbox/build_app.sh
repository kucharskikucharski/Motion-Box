#!/usr/bin/env bash
# Builds a standalone app for the system you run it on (macOS -> MotionBox.app, Linux -> binary).
# Windows: run the same PyInstaller line in a terminal and replace ":" with ";" in --add-data.
cd "$(dirname "$0")"
[ -d .venv ] || { python3 -m venv .venv && .venv/bin/pip install -r requirements.txt; }
.venv/bin/pip install pyinstaller
.venv/bin/pyinstaller --noconfirm --windowed --name MotionBox \
  --add-data "assets:assets" --add-data "icons:icons" motion_box.py
echo "Done -> dist/"
echo "User data (projects, scripts, library.json) lives in ~/MotionBox when running the packaged app."
