#!/usr/bin/env bash
# Start Accent Coach and open it in the browser.
cd "$(dirname "$0")"
(sleep 4 && xdg-open http://127.0.0.1:8765 >/dev/null 2>&1) &
exec .venv/bin/python coach.py
