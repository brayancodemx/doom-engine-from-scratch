@echo off
cd /d "%~dp0\.."
python fases_qhd\exportar_todo.py %*
if errorlevel 1 (
  echo.
  echo La exportacion no pudo completarse.
  pause
)
