#!/usr/bin/env bash
# One-time setup for Accent Coach (Linux and macOS). Safe to run again.
set -e
cd "$(dirname "$0")"

PY=""
for c in python3.12 python3.11 python3.10 python3; do
  if command -v "$c" >/dev/null 2>&1; then
    v=$("$c" -c 'import sys; print(sys.version_info[0]*100 + sys.version_info[1])')
    if [ "$v" -ge 310 ] && [ "$v" -le 312 ]; then PY="$c"; break; fi
  fi
done
if [ -z "$PY" ]; then
  echo "✗ Python 3.10, 3.11 or 3.12 is needed. See 'Step 1' in README.md."; exit 1
fi
command -v ffmpeg >/dev/null 2>&1 || { echo "✗ ffmpeg is missing. See 'Step 1' in README.md."; exit 1; }
echo "✓ Using $($PY --version) and ffmpeg"

[ -d .venv ] || "$PY" -m venv .venv
echo "… Installing (a few minutes the first time, about 1 GB)"
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q torch --index-url https://download.pytorch.org/whl/cpu
.venv/bin/pip install -q -r requirements.txt
echo "✓ Installed"

if [ ! -f .env ]; then cp .env.example .env; echo "✓ Made .env: now put your OpenAI key in it (Step 4 in README.md)"; fi
echo "Done. Start the app with: ./start.sh"
