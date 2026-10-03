@echo off
setlocal
cd /d "%~dp0"

set PY=python
where python >nul 2>nul || set PY=py -3

%PY% --version >nul 2>nul
if errorlevel 1 (
    echo Python not found. Install it and tick "Add python.exe to PATH".
    pause
    exit /b 1
)

echo Installing libraries...
%PY% -m pip install --upgrade -r requirements.txt pyinstaller
if errorlevel 1 (
    echo Could not install dependencies. Check your internet connection.
    pause
    exit /b 1
)

echo Building...
%PY% -m PyInstaller --noconfirm --onefile --windowed --collect-all imageio_ffmpeg --name ASCII-Converter ascii_converter.py
if errorlevel 1 (
    echo Build failed. See the messages above.
    pause
    exit /b 1
)

echo.
echo Done: %~dp0dist\ASCII-Converter.exe
pause
