#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
  echo "[1/3] Creating local Python environment..."
  python3 -m venv .venv
fi

echo "[2/3] Checking AI dependencies..."
if ! .venv/bin/python -c "import ultralytics,cv2,numpy,scipy,streamlit" >/dev/null 2>&1; then
  echo "Installing missing dependencies once..."
  .venv/bin/python -m pip install -q --disable-pip-version-check -r requirements.txt
fi

echo "[3/3] Starting Godrej Warehouse AI..."
exec .venv/bin/python -m streamlit run app.py --server.headless true --browser.gatherUsageStats false
