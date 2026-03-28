# 🎮 MapleStory Boss DPM Monitor - User Manual

Welcome to the **MapleStory Boss DPM Monitor**, a high-precision, GPU-accelerated tool designed to provide real-time combat analytics and professional performance reporting.

---

## 🛠️ 1. Essential First Step: Font Installation
For the interface to display correctly with its premium typography, you **must** install the **Google Sans** font provided in the package.

1.  Locate the file **`GoogleSans-VariableFont_GRAD,opsz,wght.ttf`** inside the extracted folder.
2.  Right-click the file and choose **"Install for all users"**.
3.  Restart the application if it was already open.
    *   *Note: If the font is missing, the application will fall back to Segoe UI, but the layout is optimized for Google Sans.*

---

## 🚀 2. Getting Started

### Launching the App
1.  Extract the provided `.zip` package.
2.  Run **`MapleStory_DPS_Ultimate.exe`**.
3.  Check the **System Status Bar** at the bottom:
    *   **Engine: Ready** means the OCR is loaded.
    *   **HW: NVIDIA GeForce RTX 3080** (or your GPU) indicates GPU acceleration is active.

### Setting Up the Capture
To track boss health, the app needs to know where the HP bar is:
1.  Open your MapleStory window.
2.  In the Monitor's **Configuration** section, select your game window from the dropdown list.
3.  Click **"Set Capture Region (Crop)"**.
4.  A screenshot will appear. **Click and drag** a rectangle specifically over the **boss's numeric HP values** (the actual numbers on the HP bar).
5.  Press **Escape** or release the mouse to save the region.

---

## ⌨️ 3. Hotkeys & Controls

| Hotkey | Action | Description |
| :--- | :--- | :--- |
| **F7** | **Toggle Monitoring** | Starts or stops the OCR engine. |
| **F8** | **Reset Metrics** | Clears all current damage and time data for a new run. |
| **F9** | **Toggle HUD** | Shows or hides the transparent overlay. |

### The HUD Overlay
*   **Transparency (Left Slider)**: Slide up to make the HUD more solid, or down to make it more transparent.
*   **Scale (Right Slider)**: Adjust the size of the HUD to fit your screen resolution.
*   **Dragging**: Click and drag the **top area** of the HUD to move it anywhere on your screen.

---

## 📊 4. Understanding the Metrics

*   **Remaining HP**: The last detected health of the boss.
*   **Real-time DPS**: Your damage per second calculated over the last few frames.
*   **Combat Time**: Total time spent actively dealing damage.
*   **Total Damage**: Sum of all HP lost by the boss since the start.
*   **Average DPM**: Your overall performance (Damage Per Minute).

---

## 🛡️ 5. Smart Analytics (Outlier Protection)
The monitor includes intelligent logic to filter out "visual noise" and OCR glitches:
*   **HP Jitter Filter**: If the boss's HP suddenly "increases" by more than 50,000, the data is ignored.
*   **Glitched Drop Filter**: If the HP drops by more than 500,000 in a single frame (faster than physically possible), it is ignored.
*   **Auto-Finish**: If the HP bar disappears for more than 3 seconds, the app assumes the boss is defeated and marks the combat as **FINISHED**.

---

## 📈 6. Generating Reports
After your fight, click **"GENERATE PNG REPORT"**. 
*   The app will create a professional graph showing your **DPS Curve** throughout the fight.
*   Reports are saved in the same folder as the application with the name `Boss_Report_YYYYMMDD_HHMMSS.png`.

---
*Developed for elite players. Good luck with your bossing!*
