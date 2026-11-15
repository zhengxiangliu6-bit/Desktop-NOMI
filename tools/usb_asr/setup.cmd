@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
python -c "import sys; assert (3,10) <= sys.version_info[:2] <= (3,13), 'Require 64-bit Python 3.10-3.13'; import struct; assert struct.calcsize('P')==8, 'Require 64-bit Python'"
if errorlevel 1 goto failed
if not exist .venv\Scripts\python.exe python -m venv .venv
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto failed
.venv\Scripts\python.exe setup_model.py
if errorlevel 1 goto failed
echo Ready. Run start.cmd COM3
pause
exit /b 0
:failed
echo Setup failed. Please copy the error shown above.
pause
exit /b 1
