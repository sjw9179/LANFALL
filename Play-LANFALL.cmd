@echo off
cd /d "%~dp0"
if exist "LANFALL.exe" (
  start "" "LANFALL.exe"
  exit /b
)
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
  if errorlevel 1 goto fail
  .venv\Scripts\python.exe -m pip install -r requirements.txt
  if errorlevel 1 goto fail
)
.venv\Scripts\python.exe tools\fetch_runtime.py
if errorlevel 1 goto fail
.venv\Scripts\python.exe main.py
if errorlevel 1 goto fail
exit /b
:fail
echo LANFALL could not start. See README.md and the error above.
pause
