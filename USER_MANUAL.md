# 🎮 MapleStory Boss DPM Monitor - User Manual

Welcome to the **MapleStory Boss DPM Monitor**, a high-precision, GPU-accelerated tool.

---

## 🚀 1. Getting Started

### Launching the App
1.  Extract the provided `.zip` package.
2.  Run **`MapleStory_DPM_v[VERSION].exe`**.
3.  Check the **System Status Bar** at the bottom:
    *   **Engine: Ready** means the OCR is loaded.
    *   **HW: NVIDIA GeForce RTX 3080** (or your GPU) indicates GPU acceleration is active.
    *   *Note: The required fonts (**Google Sans** and **Noto Sans TC**) are automatically loaded by the application. No manual installation is required.*

### Setting Up the Capture
To track boss health, the app needs to know where the HP bar is:
1.  Open your MapleStory window.
2.  In the Monitor's **Configuration** section, select your game window from the dropdown list.
3.  Click **"Set Capture Region (Crop)"**.
4.  A screenshot will appear. **Click and drag** a rectangle specifically over the **Boss's Name, numeric HP values, and the percentage** (e.g., "Pianus 65,000,000 (100%)").
5.  Press **Escape** or release the mouse to save the region.

---

## ⌨️ 2. Hotkeys & Controls

| Hotkey | Action | Description |
| :--- | :--- | :--- |
| **F7** | **Toggle Monitoring** | Starts or stops the OCR engine. |
| **F8** | **Reset Metrics** | Clears all current damage and time data for a new run. |
| **F9** | **Toggle HUD** | Shows or hides the transparent overlay. |

### The HUD Overlay
*   **Transparency (Left Slider)**: Slide up to make the HUD more solid, or down to make it more transparent.
*   **Scale (Right Slider)**: Adjust the size of the HUD to fit your screen resolution.
*   **Dragging**: Click and drag the **any area** of the HUD to move it anywhere on your screen.

---

## 📊 3. Understanding the Metrics

*   **Remaining HP**: The last detected health of the boss.
*   **Real-time DPS**: Your damage per second calculated over a rolling 3-second window.
*   **Combat Time**: Total time spent actively dealing damage.
*   **Total Damage**: Sum of all HP lost by the boss since the start.
*   **Average DPM**: Your overall performance (Damage Per Minute).

---

## 🛡️ 4. Smart Analytics (Outlier Protection)
The monitor includes intelligent logic to filter out "visual noise" and OCR glitches:
*   **HP Jitter Filter**: If the boss's HP suddenly "increases" by more than 50,000, the data is ignored.
*   **Glitched Drop Filter**: If the HP drops by more than 2,000,000 in a single frame (faster than physically possible), it is ignored.
*   **Auto-Finish**: If the HP bar disappears for more than **1.0 second** while the boss is at low health, the app assumes the boss is defeated and marks the combat as **FINISHED**.

---

## 📈 5. Generating Reports
After your fight, click **"GENERATE PNG REPORT"**. 
*   The app will create a professional graph showing your **DPS Curve** throughout the fight.
*   Reports are saved in the same folder as the application with the name `Boss_Report_YYYYMMDD_HHMMSS.png`.

---
*Developed for the MapleStory - Artale community by G8G.*
