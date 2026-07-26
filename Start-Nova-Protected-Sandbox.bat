@echo off
setlocal
cd /d "%~dp0"
set "NOVA_FORCE_SIMULATION=1"
set "NOVA_CONFIG=%CD%\config.sandbox.yaml"
if not exist ".venv\Scripts\python.exe" (
  echo Nova is not installed yet. Run install-windows.ps1 first.
  pause
  exit /b 1
)
echo Starting Nova Protected Sandbox at http://127.0.0.1:8788
".venv\Scripts\python.exe" run.py --config "%NOVA_CONFIG%"
endlocal
