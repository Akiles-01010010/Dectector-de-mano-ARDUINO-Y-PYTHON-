@echo off
REM Abre la camara y detecta la mano abierta para activar el Arduino.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Primero corre instalar.bat
    pause
    exit /b 1
)
".venv\Scripts\python.exe" detector_mano.py
pause
