@echo off
REM =====================================================================
REM  windows_instalar.bat
REM  Registra una tarea en el Task Scheduler de Windows para correr
REM  run_daily.py cada mañana a la hora que elijas.
REM
REM  Uso (como Administrador):
REM    windows_instalar.bat 7    -> corre a las 07:00
REM    windows_instalar.bat 8    -> corre a las 08:00
REM  (default: 7 si no se pasa argumento)
REM =====================================================================

SET HORA=%1
IF "%HORA%"=="" SET HORA=7

REM Construir hora en formato HH:00
IF %HORA% LSS 10 (SET HORA_FMT=0%HORA%:00) ELSE (SET HORA_FMT=%HORA%:00)

REM Ruta absoluta a este bat (sin el nombre del archivo)
SET PROYECTO=%~dp0..

echo Instalando tarea programada para las %HORA_FMT%...
echo Carpeta del proyecto: %PROYECTO%

schtasks /create /tn "ZobraDropiDiario" /tr "%~dp0windows_ejecutar.bat" /sc DAILY /st %HORA_FMT% /f

IF %ERRORLEVEL%==0 (
    echo.
    echo Tarea instalada correctamente.
    echo.
    echo Otros comandos utiles:
    echo   schtasks /run /tn "ZobraDropiDiario"       :: forzar corrida ahora
    echo   schtasks /delete /tn "ZobraDropiDiario"    :: eliminar la tarea
    echo   schtasks /query /tn "ZobraDropiDiario"     :: ver estado
) ELSE (
    echo.
    echo ERROR: No se pudo crear la tarea. Ejecuta este bat como Administrador.
)
