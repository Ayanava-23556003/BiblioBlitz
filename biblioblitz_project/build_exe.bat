@echo off
:: ============================================================
::  BiblioBlitz v4.1 — Root Directory Build Engine Script
::  Output: BiblioBlitz.exe (Created directly in this folder)
:: ============================================================

title BiblioBlitz Root Build Engine v4.1

echo [1/3] Upgrading pipeline architecture requirements packages...
python -m pip install --upgrade pip --quiet
python -m pip install customtkinter Pillow pyinstaller matplotlib --quiet

if errorlevel 1 (
    echo [ERROR] Pipeline packaging frameworks missed installation profiles.
    pause
    exit /b 1
)

echo [2/3] Extracting customtkinter paths configurations...
for /f "delims=" %%i in ('python -c "import customtkinter, os; print(os.path.dirname(customtkinter.__file__))"') do set CTK_PATH=%%i

echo [3/3] Running PyInstaller targeting Parent Folder Output...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "BiblioBlitz" ^
    --distpath "." ^
    --icon "%~dp0biblioblitz.ico" ^
    --add-data "%~dp0biblioblitz.ico;." ^
    --add-data "%~dp0biblioblitz.png;." ^
    --add-data "%USERPROFILE%\Downloads\states.csv;." ^
    --add-data "%CTK_PATH%;customtkinter" ^
    --hidden-import customtkinter ^
    --hidden-import tkinter ^
    --hidden-import tkinter.ttk ^
    --hidden-import PIL ^
    --hidden-import PIL.Image ^
    --hidden-import PIL.ImageDraw ^
    --hidden-import matplotlib ^
    --hidden-import matplotlib.pyplot ^
    --hidden-import matplotlib.backends.backend_tkagg ^
    --clean ^
    --noconfirm ^
    "%~dp0main.py"

if exist "%~dp0dist" rmdir /s /q "%~dp0dist"
echo ================================================================
echo   Compilation Successful! Standalone executable layout updated.
echo ================================================================
pause
