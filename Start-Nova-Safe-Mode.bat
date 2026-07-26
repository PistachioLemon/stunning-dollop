@echo off
cd /d "%~dp0"
set NOVA_FORCE_SIMULATION=1
".venv\Scripts\python.exe" desktop.py
if errorlevel 1 pause
