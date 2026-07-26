@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Nova is not installed yet. Run install-windows.ps1 in PowerShell first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" desktop.py
if errorlevel 1 pause
