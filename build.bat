@echo off
echo ======================================================
echo MapleStory Boss DPM Monitor - Auto-Versioning Build
echo ======================================================

:: 1. Auto-iterate Version
echo [1/4] Updating version...
python update_version.py

:: 2. Setup Virtual Environment
echo [2/4] Creating virtual environment...
if not exist venv (
    python -m venv venv
)
call .\venv\Scripts\activate

:: 3. Install GPU-enabled dependencies
echo [3/4] Ensuring dependencies (PyTorch + cu121)...
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install pyinstaller easyocr seaborn scipy mss keyboard pandas matplotlib pygetwindow pillow

:: 4. Run PyInstaller
echo [4/4] Building executable with PyInstaller...
pyinstaller --noconfirm MapleStory_DPM.spec

:: 5. Copy Manual
echo [5/5] Adding documentation...
set "VERSION_VAL="
for /f "delims=" %%i in (VERSION) do set "VERSION_VAL=%%i"
copy USER_MANUAL.pdf "dist\MapleStory_DPM_v%VERSION_VAL%\" 2>nul
copy USER_MANUAL_ZH.pdf "dist\MapleStory_DPM_v%VERSION_VAL%\" 2>nul

echo ======================================================
echo Build Complete! Check the 'dist' folder.
echo ======================================================
pause
