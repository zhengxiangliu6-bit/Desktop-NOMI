@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Run setup.cmd first, or copy this update into your existing pc folder.
  pause
  exit /b 1
)
set NOMI_ASR_PORT=%~1
if "%NOMI_ASR_PORT%"=="" set NOMI_ASR_PORT=COM3
.venv\Scripts\python.exe transcribe.py --voice-control --port "%NOMI_ASR_PORT%" %2 %3 %4 %5 %6 %7
pause
