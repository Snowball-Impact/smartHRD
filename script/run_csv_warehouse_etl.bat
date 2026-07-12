@echo off
setlocal

cd /d "%~dp0.."

set MONTHS_BACK=6
set MONTHS_FORWARD=6

if not "%SMART_HRD_MONTHS_BACK%"=="" set MONTHS_BACK=%SMART_HRD_MONTHS_BACK%
if not "%SMART_HRD_MONTHS_FORWARD%"=="" set MONTHS_FORWARD=%SMART_HRD_MONTHS_FORWARD%

python script\csv_warehouse_etl.py --api all --months-back %MONTHS_BACK% --months-forward %MONTHS_FORWARD% --workers 2 --progress-every-pages 10 %*

exit /b %ERRORLEVEL%
