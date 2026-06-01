@echo off
:: ============================================================
::  BiblioBlitz v3.2 — Build EXE
::  Place this file in the SAME folder as:
::    - biblioblitz.py
::    - biblioblitz.ico
::  Output: dist\BiblioBlitz.exe
:: ============================================================

title BiblioBlitz Build

echo.
echo   ██████╗ ██╗██████╗ ██╗     ██╗ ██████╗ ██████╗ ██╗     ██╗████████╗███████╗
echo   ██╔══██╗██║██╔══██╗██║     ██║██╔═══██╗██╔══██╗██║     ██║╚══██╔══╝╚══███╔╝
echo   ██████╔╝██║██████╔╝██║     ██║██║   ██║██████╔╝██║     ██║   ██║     ███╔╝
echo   ██╔══██╗██║██╔══██╗██║     ██║██║   ██║██╔══██╗██║     ██║   ██║    ███╔╝
echo   ██████╔╝██║██████╔╝███████╗██║╚██████╔╝██████╔╝███████╗██║   ██║   ███████╗
echo   ╚═════╝ ╚═╝╚═════╝ ╚══════╝╚═╝ ╚═════╝ ╚═════╝ ╚══════╝╚═╝   ╚═╝   ╚══════╝
echo                              Build Script  v3.2
echo.

:: ── Check Python ──────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH.
    echo         Download from https://www.python.org/downloads/
    echo         Check "Add Python to PATH" during install.
    pause
    exit /b 1
)

:: ── Install dependencies ──────────────────────────────────────
echo [1/3] Installing / updating packages...
python -m pip install --upgrade pip --quiet
python -m pip install customtkinter Pillow pyinstaller --quiet

if errorlevel 1 (
    echo [ERROR] Failed to install packages. Check your internet connection.
    pause
    exit /b 1
)

:: ── Get customtkinter path ────────────────────────────────────
echo [2/3] Locating customtkinter data files...
for /f "delims=" %%i in ('python -c "import customtkinter, os; print(os.path.dirname(customtkinter.__file__))"') do set CTK_PATH=%%i

if "%CTK_PATH%"=="" (
    echo [ERROR] Could not locate customtkinter path.
    pause
    exit /b 1
)
echo        customtkinter path: %CTK_PATH%

:: ── Build EXE ────────────────────────────────────────────────
echo [3/3] Running PyInstaller...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "BiblioBlitz" ^
    --icon "%~dp0biblioblitz.ico" ^
    --add-data "%~dp0biblioblitz.ico;." ^
    --add-data "%~dp0biblioblitz.png;." ^
    --add-data "%CTK_PATH%;customtkinter" ^
    --hidden-import customtkinter ^
    --hidden-import tkinter ^
    --hidden-import tkinter.ttk ^
    --hidden-import PIL ^
    --hidden-import PIL.Image ^
    --hidden-import PIL.ImageDraw ^
    --clean ^
    --noconfirm ^
    "%~dp0biblioblitz.py"

if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller failed. See above for details.
    pause
    exit /b 1
)

echo.
echo ================================================================
echo   BiblioBlitz.exe is ready in the  dist\  folder.
echo   Users need NOTHING installed — just the EXE.
echo ================================================================
echo.

if exist "%~dp0dist\BiblioBlitz.exe" (
    explorer "%~dp0dist"
)

pause