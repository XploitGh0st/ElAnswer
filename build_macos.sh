#!/bin/bash
# ============================================================
# ElAnswer Build Script for macOS
# Creates a standalone .app bundle using PyInstaller
# ============================================================

set -e

echo ""
echo "==============================================="
echo "       ElAnswer Build Script v1.3.0"
echo "              (macOS)"
echo "==============================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed!"
    echo "Please install Python 3.8+ using Homebrew:"
    echo "  brew install python3"
    exit 1
fi

echo "[OK] Python found: $(python3 --version)"

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

# Create .icns icon for macOS if not exists
if [ ! -f "assets/logo.icns" ]; then
    echo "[INFO] Creating macOS icon..."
    # Create iconset directory
    mkdir -p assets/ElAnswer.iconset
    
    # Generate different sizes
    sips -z 16 16     assets/logo.png --out assets/ElAnswer.iconset/icon_16x16.png 2>/dev/null || true
    sips -z 32 32     assets/logo.png --out assets/ElAnswer.iconset/icon_16x16@2x.png 2>/dev/null || true
    sips -z 32 32     assets/logo.png --out assets/ElAnswer.iconset/icon_32x32.png 2>/dev/null || true
    sips -z 64 64     assets/logo.png --out assets/ElAnswer.iconset/icon_32x32@2x.png 2>/dev/null || true
    sips -z 128 128   assets/logo.png --out assets/ElAnswer.iconset/icon_128x128.png 2>/dev/null || true
    sips -z 256 256   assets/logo.png --out assets/ElAnswer.iconset/icon_128x128@2x.png 2>/dev/null || true
    sips -z 256 256   assets/logo.png --out assets/ElAnswer.iconset/icon_256x256.png 2>/dev/null || true
    sips -z 512 512   assets/logo.png --out assets/ElAnswer.iconset/icon_256x256@2x.png 2>/dev/null || true
    sips -z 512 512   assets/logo.png --out assets/ElAnswer.iconset/icon_512x512.png 2>/dev/null || true
    sips -z 1024 1024 assets/logo.png --out assets/ElAnswer.iconset/icon_512x512@2x.png 2>/dev/null || true
    
    # Create .icns file
    iconutil -c icns assets/ElAnswer.iconset -o assets/logo.icns 2>/dev/null || true
    
    # Clean up
    rm -rf assets/ElAnswer.iconset
    
    if [ -f "assets/logo.icns" ]; then
        echo "[OK] macOS icon created"
    else
        echo "[WARNING] Could not create .icns icon, using PNG"
    fi
fi

# Clean previous builds
echo ""
echo "[INFO] Cleaning previous builds..."
rm -rf dist build
echo "[OK] Clean complete"

# Determine icon file
ICON_FILE="assets/logo.png"
if [ -f "assets/logo.icns" ]; then
    ICON_FILE="assets/logo.icns"
fi

# Build the executable
echo ""
echo "[INFO] Building ElAnswer.app..."
echo "This may take 2-5 minutes..."
echo ""

pyinstaller \
    --name="ElAnswer" \
    --onefile \
    --windowed \
    --icon="$ICON_FILE" \
    --add-data="assets:assets" \
    --hidden-import="PIL._tkinter_finder" \
    --hidden-import="pystray._darwin" \
    --hidden-import="google.generativeai" \
    --osx-bundle-identifier="com.xploitgh0st.elanswer" \
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
    echo "  1. Copy dist/ElAnswer to /Applications or desired location"
    echo "  2. Run: ./ElAnswer"
    echo ""
    echo "IMPORTANT - Screen Recording Permission:"
    echo "  For screenshot capture to work, grant permission in:"
    echo "  System Preferences > Security & Privacy > Privacy > Screen Recording"
    echo "  Add 'ElAnswer' to the allowed apps."
    echo ""
    echo "IMPORTANT - Accessibility Permission (for hotkeys):"
    echo "  System Preferences > Security & Privacy > Privacy > Accessibility"
    echo "  Add 'ElAnswer' to the allowed apps."
    echo ""
else
    echo ""
    echo "==============================================="
    echo "           BUILD FAILED!"
    echo "==============================================="
    echo ""
    echo "Common issues:"
    echo "  - Missing dependencies (run: pip install -r requirements.txt)"
    echo "  - Missing assets/logo.png"
    echo "  - Xcode Command Line Tools not installed"
    echo "    Install with: xcode-select --install"
    echo ""
    exit 1
fi
