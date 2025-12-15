@echo off
REM ============================================================
REM ElAnswer Build Script for Windows
REM Creates a standalone executable using PyInstaller
REM ============================================================

echo.
echo ===============================================
echo        ElAnswer Build Script v1.2.0
echo ===============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

REM Check for virtual environment
if exist "venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
)

REM Install/upgrade pip
echo.
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip

REM Install requirements
echo.
echo [INFO] Installing dependencies...
pip install -r requirements.txt

REM Install PyInstaller if not present
echo.
echo [INFO] Installing PyInstaller...
pip install pyinstaller

REM Clean previous builds
echo.
echo [INFO] Cleaning previous builds...
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build

REM Build the executable
echo.
echo [INFO] Building ElAnswer.exe...
echo This may take a few minutes...
echo.

pyinstaller ElAnswer.spec --clean

REM Check if build was successful
if exist "dist\ElAnswer.exe" (
    echo.
    echo ===============================================
    echo        BUILD SUCCESSFUL!
    echo ===============================================
    echo.
    echo Executable created at: dist\ElAnswer.exe
    echo File size: 
    for %%A in (dist\ElAnswer.exe) do echo   %%~zA bytes (%%~zA bytes / 1048576 = MB approx)
    echo.
    echo To distribute:
    echo   1. Copy dist\ElAnswer.exe to your desired location
    echo   2. Users can run ElAnswer.exe directly
    echo   3. Config and history files will be created next to the exe
    echo.
) else (
    echo.
    echo ===============================================
    echo        BUILD FAILED!
    echo ===============================================
    echo.
    echo Check the output above for errors.
    echo Common issues:
    echo   - Missing dependencies
    echo   - Antivirus blocking PyInstaller
    echo   - Missing assets/logo.png
    echo.
)

pause
