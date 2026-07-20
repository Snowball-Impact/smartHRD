@echo off
setlocal

cd /d "%~dp0.."

set MONTHS_BACK=6
set MONTHS_FORWARD=6
set PERIOD_RETRIES=1

if not "%SMART_HRD_MONTHS_BACK%"=="" set MONTHS_BACK=%SMART_HRD_MONTHS_BACK%
if not "%SMART_HRD_MONTHS_FORWARD%"=="" set MONTHS_FORWARD=%SMART_HRD_MONTHS_FORWARD%
if not "%SMART_HRD_PERIOD_RETRIES%"=="" set PERIOD_RETRIES=%SMART_HRD_PERIOD_RETRIES%

python script\csv_warehouse_etl.py --api all --months-back %MONTHS_BACK% --months-forward %MONTHS_FORWARD% --period-retries %PERIOD_RETRIES% --workers 2 --progress-every-pages 10 %*

exit /b %ERRORLEVEL%
