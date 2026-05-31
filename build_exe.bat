@echo off
:: ============================================================
::  BiblioBlitz v3 — Build EXE
::  Run this script to produce dist\BiblioBlitz_v3.2.exe
::  Requires: Python 3.9+ with pip  (no R, no separate install)
::  Works on any Windows 10/11 PC (32-bit or 64-bit)
:: ============================================================

title BiblioBlitz v3 Build

echo.
echo   ██████╗ ██╗██████╗ ██╗     ██╗ ██████╗ ██████╗ ██╗     ██╗████████╗███████╗
echo   ██╔══██╗██║██╔══██╗██║     ██║██╔═══██╗██╔══██╗██║     ██║╚══██╔══╝╚══███╔╝
echo   ██████╔╝██║██████╔╝██║     ██║██║   ██║██████╔╝██║     ██║   ██║     ███╔╝
echo   ██╔══██╗██║██╔══██╗██║     ██║██║   ██║██╔══██╗██║     ██║   ██║    ███╔╝
echo   ██████╔╝██║██████╔╝███████╗██║╚██████╔╝██████╔╝███████╗██║   ██║   ███████╗
echo   ╚═════╝ ╚═╝╚═════╝ ╚══════╝╚═╝ ╚═════╝ ╚═════╝ ╚══════╝╚═╝   ╚═╝   ╚══════╝
echo                              Build Script  v3.2
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH.
    echo         Download Python from https://www.python.org/downloads/
    echo         Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)

echo [1/3] Installing / updating pip packages...
python -m pip install --upgrade pip --quiet
python -m pip install customtkinter Pillow pyinstaller --quiet

if errorlevel 1 (
    echo [ERROR] Failed to install packages. Check your internet connection.
    pause
    exit /b 1
)

echo [2/3] Locating customtkinter data files...
for /f "delims=" %%i in ('python -c "import customtkinter, os; print(os.path.dirname(customtkinter.__file__))"') do set CTK_PATH=%%i

if "%CTK_PATH%"=="" (
    echo [ERROR] Could not locate customtkinter path.
    pause
    exit /b 1
)
echo        customtkinter path: %CTK_PATH%

echo [3/3] Running PyInstaller...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "BiblioBlitz_v3.2" ^
    --icon NONE ^
    --add-data "C:\Users\ayanp\Downloads\BiblioBlitz_v3\BiblioBlitz_v3\biblioblitz.ico;." ^
    --hidden-import customtkinter ^
    --hidden-import tkinter ^
    --hidden-import tkinter.ttk ^
    --hidden-import PIL ^
    --hidden-import PIL.Image ^
    --hidden-import PIL.ImageDraw ^
    --clean ^
    --noconfirm ^
    biblioblitz.py

if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller failed. See above for details.
    pause
    exit /b 1
)

echo.
echo ================================================================
echo   BiblioBlitz_v3.2.exe is ready in the  dist\  folder.
echo.
echo   You can copy it to ANY Windows PC (32-bit or 64-bit) and
echo   run it immediately — no R, no Python, no extra installs.
echo   Internet connection required for searching and downloading.
echo ================================================================
echo.

if exist "dist\BiblioBlitz_v3.2.exe" (
    explorer dist
)

pause
