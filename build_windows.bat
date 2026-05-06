@echo off
echo Installing dependencies...
pip install -r requirements.txt

echo Building executable...
python -m pyinstaller --onefile --windowed --name IMG-CONVert --icon=NONE image_converter.py

echo Done! Executable is in the dist folder.
pause
