@echo off
setlocal
cd /d "%~dp0"
title Godrej Warehouse AI

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creating local Python environment...
    py -3 -m venv .venv
    if errorlevel 1 (
        echo Python 3 is required. Install Python 3.10-3.12 and run this file again.
        pause
        exit /b 1
    )
)

echo [2/3] Checking AI dependencies...
.venv\Scripts\python.exe -c "import ultralytics,cv2,numpy,scipy,streamlit" >nul 2>&1
if errorlevel 1 (
    echo Installing missing dependencies once...
    .venv\Scripts\python.exe -m pip install -q --disable-pip-version-check -r requirements.txt
    if errorlevel 1 (
        echo Dependency installation failed. Check your internet connection and Python version.
        pause
        exit /b 1
    )
)

echo [3/3] Starting Godrej Warehouse AI...
.venv\Scripts\python.exe -m streamlit run app.py --server.headless true --browser.gatherUsageStats false

endlocal
