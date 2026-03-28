@echo off
echo ======================================================
echo MapleStory Boss DPM Monitor - GPU Build Script
echo ======================================================

:: 1. Setup Virtual Environment
echo [1/3] Creating virtual environment...
python -m venv venv
call .\venv\Scripts\activate

:: 2. Install GPU-enabled dependencies
echo [2/3] Installing GPU-enabled dependencies (PyTorch + cu121)...
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install pyinstaller easyocr seaborn scipy mss keyboard pandas matplotlib pygetwindow pillow

:: 3. Run PyInstaller
echo [3/3] Building executable with PyInstaller...
pyinstaller --noconfirm MapleStory_DPM_v20260329.2.spec

echo ======================================================
echo Build Complete! Check the 'dist' folder.
echo ======================================================
pause
