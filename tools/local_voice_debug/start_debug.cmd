@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set NOMI_TRACE_PORT=%~1
if "%NOMI_TRACE_PORT%"=="" set NOMI_TRACE_PORT=COM3
python "%~dp0monitor.py" --port "%NOMI_TRACE_PORT%" %2 %3 %4 %5 %6 %7
pause
