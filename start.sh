#!/usr/bin/env bash
# Start Accent Coach and open it in the browser.
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then echo "Run ./setup.sh first."; exit 1; fi
URL=http://127.0.0.1:8765
echo "Accent Coach is starting at $URL (press Ctrl+C here to stop it)"
(sleep 4 && { command -v xdg-open >/dev/null && xdg-open $URL || open $URL; } >/dev/null 2>&1) &
exec .venv/bin/python coach.py
