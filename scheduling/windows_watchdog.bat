@echo off
REM Corre watchdog.py desde la carpeta raiz del proyecto.
cd /d "%~dp0.."
python watchdog.py >> logs\watchdog.log 2>&1
