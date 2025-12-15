#!/bin/bash
# ============================================================
# ElAnswer Build Script for Linux
# Creates a standalone executable using PyInstaller
# ============================================================

set -e

echo ""
echo "==============================================="
echo "       ElAnswer Build Script v1.3.0"
echo "              (Linux)"
echo "==============================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed!"
    echo "Please install Python 3.8+ using your package manager"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv python3-tk"
    echo "  Fedora: sudo dnf install python3 python3-pip python3-tkinter"
    exit 1
fi

echo "[OK] Python found: $(python3 --version)"

# Check for required system dependencies
echo "[INFO] Checking system dependencies..."

# Check for tkinter
if ! python3 -c "import tkinter" 2>/dev/null; then
    echo "[WARNING] tkinter not found. Install with:"
    echo "  Ubuntu/Debian: sudo apt install python3-tk"
    echo "  Fedora: sudo dnf install python3-tkinter"
fi

# Check for assets
if [ ! -f "assets/logo.png" ]; then
    echo "[ERROR] assets/logo.png not found!"
    exit 1
fi
echo "[OK] Assets folder found"

# Create/activate virtual environment
if [ -d "venv" ]; then
    echo "[INFO] Activating existing virtual environment..."
    source venv/bin/activate
else
    echo "[INFO] Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
fi

# Upgrade pip
echo ""
echo "[INFO] Upgrading pip..."
pip install --upgrade pip --quiet

# Install requirements
echo "[INFO] Installing dependencies..."
pip install -r requirements.txt --quiet
echo "[OK] Dependencies installed"

# Clean previous builds
echo ""
echo "[INFO] Cleaning previous builds..."
rm -rf dist build
echo "[OK] Clean complete"

# Build the executable
echo ""
echo "[INFO] Building ElAnswer..."
echo "This may take 2-5 minutes..."
echo ""

pyinstaller \
    --name="ElAnswer" \
    --onefile \
    --windowed \
    --add-data="assets:assets" \
    --hidden-import="PIL._tkinter_finder" \
    --hidden-import="pystray._xorg" \
    --hidden-import="pystray._appindicator" \
    --hidden-import="google.generativeai" \
    --hidden-import="pyscreenshot" \
    --clean \
    --noconfirm \
    main.py

# Check if build was successful
if [ -f "dist/ElAnswer" ]; then
    SIZE=$(du -h dist/ElAnswer | cut -f1)
    
    echo ""
    echo "==============================================="
    echo "           BUILD SUCCESSFUL!"
    echo "==============================================="
    echo ""
    echo "Executable: dist/ElAnswer"
    echo "Size: $SIZE"
    echo ""
    echo "Distribution Instructions:"
    echo "  1. Copy dist/ElAnswer to your desired location"
    echo "  2. Make it executable: chmod +x ElAnswer"
    echo "  3. Run with: ./ElAnswer"
    echo "  4. Note: May require running with sudo for keyboard hooks"
    echo ""
    echo "System Tray Requirements:"
    echo "  Ubuntu: sudo apt install libappindicator3-1 gir1.2-appindicator3-0.1"
    echo "  Fedora: sudo dnf install libappindicator-gtk3"
    echo ""
else
    echo ""
    echo "==============================================="
    echo "           BUILD FAILED!"
    echo "==============================================="
    echo ""
    echo "Common issues:"
    echo "  - Missing dependencies (run: pip install -r requirements.txt)"
    echo "  - Missing system packages (python3-tk, libappindicator)"
    echo "  - Missing assets/logo.png"
    echo ""
    exit 1
fi
