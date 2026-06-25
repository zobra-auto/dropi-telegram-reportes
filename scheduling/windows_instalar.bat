@echo off
REM =====================================================================
REM  windows_instalar.bat
REM  Instala DOS tareas en el Task Scheduler de Windows:
REM    1. Reporte diario (run_daily.py) a la hora elegida
REM    2. Watchdog (watchdog.py) 2 horas despues
REM
REM  Uso (ejecutar como Administrador):
REM    windows_instalar.bat 7    -> reporte 07:00, watchdog 09:00
REM    windows_instalar.bat 8    -> reporte 08:00, watchdog 10:00
REM  Default: 7 si no se pasa argumento
REM =====================================================================

SET HORA=%1
IF "%HORA%"=="" SET HORA=7

SET /A HORA_WD=%HORA%+2

REM Formato HH:00
IF %HORA% LSS 10 (SET HORA_FMT=0%HORA%:00) ELSE (SET HORA_FMT=%HORA%:00)
IF %HORA_WD% LSS 10 (SET HORA_WD_FMT=0%HORA_WD%:00) ELSE (SET HORA_WD_FMT=%HORA_WD%:00)

SET BAT_DIR=%~dp0

echo Instalando tareas programadas...
echo Reporte: %HORA_FMT% ^| Watchdog: %HORA_WD_FMT%
echo.

REM --- Tarea 1: Reporte diario ---
schtasks /create /tn "ZobraDropiDiario" /tr "%BAT_DIR%windows_ejecutar.bat" ^
  /sc DAILY /st %HORA_FMT% /f ^
  /ru "%USERNAME%" ^
  /rl HIGHEST

IF %ERRORLEVEL%==0 (
    echo [OK] Reporte diario instalado a las %HORA_FMT%
) ELSE (
    echo [ERROR] Fallo al crear tarea de reporte. Ejecuta como Administrador.
    goto :fin
)

REM --- Tarea 2: Watchdog ---
schtasks /create /tn "ZobraDropiWatchdog" /tr "%BAT_DIR%windows_watchdog.bat" ^
  /sc DAILY /st %HORA_WD_FMT% /f ^
  /ru "%USERNAME%" ^
  /rl HIGHEST

IF %ERRORLEVEL%==0 (
    echo [OK] Watchdog instalado a las %HORA_WD_FMT%
) ELSE (
    echo [ERROR] Fallo al crear tarea de watchdog.
    goto :fin
)

REM --- Activar "despertar el equipo" para ambas tareas ---
powershell -Command "& {$t=Get-ScheduledTask 'ZobraDropiDiario'; $t.Settings.WakeToRun=$true; Set-ScheduledTask -InputObject $t}" 2>nul
powershell -Command "& {$t=Get-ScheduledTask 'ZobraDropiWatchdog'; $t.Settings.WakeToRun=$true; Set-ScheduledTask -InputObject $t}" 2>nul
echo [OK] Wake-to-run activado (el PC se despertara automaticamente)

echo.
echo =========================================
echo Sistema instalado:
echo   %HORA_FMT% - Reporte Dropi
echo   %HORA_WD_FMT% - Watchdog (recuperacion automatica)
echo.
echo Comandos utiles:
echo   schtasks /run /tn "ZobraDropiDiario"     :: forzar reporte ahora
echo   schtasks /run /tn "ZobraDropiWatchdog"   :: forzar watchdog ahora
echo   schtasks /query /tn "ZobraDropiDiario"   :: ver estado
echo =========================================

:fin
