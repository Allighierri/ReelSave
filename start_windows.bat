@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv
    if errorlevel 1 goto error
)
".venv\Scripts\python.exe" -c "import PySide6, yt_dlp" >nul 2>&1
if errorlevel 1 (
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto error
)
".venv\Scripts\python.exe" main.py
if errorlevel 1 goto error
exit /b 0
:error
echo ReelSave could not start. Install Python 3.11+ and see README.md.
pause
exit /b 1
