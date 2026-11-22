@echo off
setlocal
cd /d "%~dp0"

echo ==========================================
echo   My Dashboard - starting...
echo ==========================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Please install Python 3.10+ from https://www.python.org/downloads/
  echo Then run this file again.
  pause
  exit /b 1
)

echo Installing/checking dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo Failed to install dependencies. Check your internet connection or Python setup.
  pause
  exit /b 1
)

findstr /B /C:"SEQTA_MODE=playwright" .env >nul 2>nul
if not errorlevel 1 (
  echo Installing/checking Playwright for SEQTA automation...
  python -m pip install -r requirements-seqta.txt
  python -m playwright install chromium
)


echo.
echo Starting dashboard at http://127.0.0.1:8000
echo (Close this window to stop the dashboard)
echo.
start "" http://127.0.0.1:8000
python run.py

echo.
echo Dashboard stopped.
pause
