@echo off
cd /d "%~dp0"
set "CENITEG_DATA_DIR=%~dp0datos_locales"
set "PLAYWRIGHT_BROWSERS_PATH=%~dp0.browsers"
if not exist ".venv\Scripts\python.exe" (
  echo Prepare el entorno siguiendo PRESENTACION_MVP.md
  pause
  exit /b 1
)
".venv\Scripts\python.exe" main.py
if errorlevel 1 pause
