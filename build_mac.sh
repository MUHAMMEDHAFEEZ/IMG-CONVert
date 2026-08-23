#!/bin/bash

echo "========================================"
echo " Building IMG-CONVert for macOS "
echo "========================================"

# Check if running on macOS (Darwin)
if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "⚠️  تنبيه: أنت تعمل حالياً على نظام $(uname -s) وليس macOS!"
    echo "لا يمكن لـ PyInstaller إنشاء تطبيق Mac (.app) مباشرة من نظام Linux/Windows."
    echo ""
    echo "💡 للحصول على نسخة Mac جاهزة لديك خياران:"
    echo "1. ارفع المشروع إلى GitHub وسيتم بناؤه تلقائياً لـ macOS عبر GitHub Actions."
    echo "2. أو قم بتشغيل هذا السكربت داخل جهاز Mac حقيقي."
    echo "========================================"
    exit 1
fi

# Set up virtual environment
echo "Setting up Python virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate

# Ensure dependencies are installed
echo "Installing python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt || pip install --break-system-packages -r requirements.txt

# Clean previous build artifacts
rm -rf build dist

# Build macOS .app bundle
echo "Building macOS application bundle..."
pyinstaller --noconfirm --onedir --windowed --name "IMG-CONVert" image_converter.py

# Optional: Create a zip archive for distribution
if [ -d "dist/IMG-CONVert.app" ]; then
    echo "Creating zip archive for distribution..."
    cd dist
    zip -r "IMG-CONVert-macOS.zip" "IMG-CONVert.app"
    cd ..
    echo "========================================"
    echo " SUCCESS!"
    echo " App created at: dist/IMG-CONVert.app"
    echo " Zip created at: dist/IMG-CONVert-macOS.zip"
    echo "========================================"
else
    echo "Build failed. Check error messages above."
fi

