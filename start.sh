#!/usr/bin/env bash
# Linux / macOS: зависимости устанавливаются только при первом запуске.
set -e
cd -- "$(dirname -- "$0")"
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi
if ! .venv/bin/python -c 'import PySide6, yt_dlp' >/dev/null 2>&1; then
  .venv/bin/python -m pip install -r requirements.txt
fi
exec .venv/bin/python main.py
