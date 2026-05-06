@echo off
echo Installing dependencies...
pip install PyQt6 Pillow pyinstaller

echo Building executable...
python -m pyinstaller --onefile --windowed --name IMG-CONVert --icon=NONE image_converter.py

echo Done! Executable is in dist folder.
pause
