#!/usr/bin/env bash
# Double-click friendly launcher: creates a private Python environment on first run.
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv || { echo "Python 3 is required (https://www.python.org/downloads/)"; exit 1; }
  .venv/bin/pip install --upgrade pip
  .venv/bin/pip install -r requirements.txt
fi
.venv/bin/python motion_box.py "$@"
