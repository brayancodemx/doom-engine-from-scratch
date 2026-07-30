@echo off
cd /d "%~dp0"
python main.py %*
if errorlevel 1 (
  echo.
  echo Si falta Pygame, ejecuta:  pip install -r requirements.txt
  pause
)
