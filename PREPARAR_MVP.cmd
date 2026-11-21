@echo off
setlocal
set "PYTHONUNBUFFERED=1"
cd /d "%~dp0"
title Preparar CENITEG

if exist ".venv\Scripts\python.exe" goto entorno
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if not errorlevel 1 goto lanzador
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if not errorlevel 1 goto python
echo No se encontro Python 3.10 o superior.
echo Instale Python para Windows con pip y Tcl/Tk desde https://www.python.org/downloads/windows/
echo Despues vuelva a ejecutar PREPARAR_MVP.cmd.
set "RESULTADO=1"
goto terminar

:entorno
".venv\Scripts\python.exe" "scripts\preparar_entorno.py" %*
set "RESULTADO=%ERRORLEVEL%"
goto terminar

:lanzador
py -3 "scripts\preparar_entorno.py" %*
set "RESULTADO=%ERRORLEVEL%"
goto terminar

:python
python "scripts\preparar_entorno.py" %*
set "RESULTADO=%ERRORLEVEL%"

:terminar
if not "%RESULTADO%"=="0" echo No se completo la preparacion. Revise el mensaje anterior.
if not defined CENITEG_SIN_PAUSA pause
exit /b %RESULTADO%
