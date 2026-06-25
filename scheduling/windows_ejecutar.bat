@echo off
REM =====================================================================
REM  windows_ejecutar.bat
REM  Corre run_daily.py desde la carpeta raíz del proyecto.
REM  El Task Scheduler de Windows apunta a este .bat.
REM  NO editar — es generado por Claude durante la configuración.
REM =====================================================================

cd /d "%~dp0.."
python run_daily.py >> logs\daily.log 2>&1
