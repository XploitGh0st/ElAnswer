<#
.SYNOPSIS
    ElAnswer Build Script for Windows (PowerShell)
    
.DESCRIPTION
    Creates a standalone executable using PyInstaller.
    Run this script to build ElAnswer.exe for distribution.

.EXAMPLE
    .\build.ps1
    
.NOTES
    Author: XploitGh0st
    Version: 1.2.0
#>

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "       ElAnswer Build Script v1.2.0" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python is not installed or not in PATH!" -ForegroundColor Red
    Write-Host "Please install Python 3.8+ from https://python.org"
    exit 1
}

# Check for assets
if (-not (Test-Path "assets\logo.png")) {
    Write-Host "[ERROR] assets\logo.png not found!" -ForegroundColor Red
    Write-Host "Please ensure the assets folder is present."
    exit 1
}
Write-Host "[OK] Assets folder found" -ForegroundColor Green

# Create/activate virtual environment
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "[INFO] Activating existing virtual environment..." -ForegroundColor Yellow
    & .\venv\Scripts\Activate.ps1
} else {
    Write-Host "[INFO] Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    & .\venv\Scripts\Activate.ps1
}

# Upgrade pip
Write-Host ""
Write-Host "[INFO] Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet

# Install requirements
Write-Host "[INFO] Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt --quiet
Write-Host "[OK] Dependencies installed" -ForegroundColor Green

# Clean previous builds
Write-Host ""
Write-Host "[INFO] Cleaning previous builds..." -ForegroundColor Yellow
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
Write-Host "[OK] Clean complete" -ForegroundColor Green

# Build the executable
Write-Host ""
Write-Host "[INFO] Building ElAnswer.exe..." -ForegroundColor Yellow
Write-Host "This may take 2-5 minutes..." -ForegroundColor Gray
Write-Host ""

try {
    pyinstaller ElAnswer.spec --clean --noconfirm 2>&1 | ForEach-Object {
        if ($_ -match "error|Error|ERROR") {
            Write-Host $_ -ForegroundColor Red
        } elseif ($_ -match "warning|Warning|WARNING") {
            Write-Host $_ -ForegroundColor Yellow
        } else {
            Write-Host $_ -ForegroundColor Gray
        }
    }
} catch {
    Write-Host "[ERROR] Build failed: $_" -ForegroundColor Red
    exit 1
}

# Check if build was successful
if (Test-Path "dist\ElAnswer.exe") {
    $fileInfo = Get-Item "dist\ElAnswer.exe"
    $sizeInMB = [math]::Round($fileInfo.Length / 1MB, 2)
    
    Write-Host ""
    Write-Host "===============================================" -ForegroundColor Green
    Write-Host "           BUILD SUCCESSFUL!" -ForegroundColor Green
    Write-Host "===============================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Executable: dist\ElAnswer.exe" -ForegroundColor Cyan
    Write-Host "Size: $sizeInMB MB" -ForegroundColor Cyan
    Write-Host "Created: $($fileInfo.CreationTime)" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Distribution Instructions:" -ForegroundColor Yellow
    Write-Host "  1. Copy dist\ElAnswer.exe to your desired location"
    Write-Host "  2. Users can run ElAnswer.exe directly (no install needed)"
    Write-Host "  3. Config and history files are created next to the exe"
    Write-Host "  4. First run will prompt for Gemini API key"
    Write-Host ""
    
    # Ask to open folder
    $openFolder = Read-Host "Open output folder? (y/n)"
    if ($openFolder -eq "y" -or $openFolder -eq "Y") {
        Start-Process explorer.exe -ArgumentList "dist"
    }
} else {
    Write-Host ""
    Write-Host "===============================================" -ForegroundColor Red
    Write-Host "           BUILD FAILED!" -ForegroundColor Red
    Write-Host "===============================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Common issues:" -ForegroundColor Yellow
    Write-Host "  - Missing dependencies (run: pip install -r requirements.txt)"
    Write-Host "  - Antivirus blocking PyInstaller"
    Write-Host "  - Missing assets/logo.png"
    Write-Host "  - Insufficient disk space"
    Write-Host ""
    exit 1
}

Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
