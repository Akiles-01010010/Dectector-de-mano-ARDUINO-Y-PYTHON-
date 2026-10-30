@echo off
REM Crea el entorno de Python (carpeta .venv) e instala las librerias.
REM Solo hace falta correrlo una vez.
cd /d "%~dp0"
py -3.12 -m venv .venv
if errorlevel 1 (
    echo No se pudo crear el entorno. Necesitas Python 3.12 instalado.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
echo.
echo Listo. Ahora abre iniciar.bat
pause
