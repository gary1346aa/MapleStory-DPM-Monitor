# MapleStory Boss DPM Monitor - User Manual

MapleStory Boss DPM Monitor is a combat analytics tool using GPU-accelerated OCR.

---

## 1. Getting Started

### Launching the App
1.  Extract the provided `.zip` package.
2.  Run **`MapleStory_DPM_v[VERSION].exe`**.
3.  Check the **System Status Bar** at the bottom:
    *   **Engine: Ready** means the OCR is loaded.
    *   **HW: NVIDIA GeForce RTX 3080** (or your GPU) indicates GPU acceleration is active.
    *   *Note: The Google Sans font is loaded by the application automatically.*

### Setting Up the Capture
To track boss health, the app needs to define the HP bar region:
1.  Open your MapleStory window.
2.  In the Monitor's **Configuration** section, select your game window from the dropdown list.
3.  Click **"Set Capture Region (Crop)"**.
4.  A screenshot will appear. **Click and drag** a rectangle over the **Boss's Name, numeric HP values, and the percentage**.
5.  Press **Escape** or release the mouse to save the region.

---

## 2. Hotkeys & Controls

| Hotkey | Action | Description |
| :--- | :--- | :--- |
| **F7** | **Toggle Monitoring** | Starts or stops the OCR engine. |
| **F8** | **Reset Metrics** | Clears current data for a new run. |
| **F9** | **Toggle HUD** | Shows or hides the overlay. |

### The HUD Overlay
*   **Transparency (Left Slider)**: Adjusts the HUD opacity.
*   **Scale (Right Slider)**: Adjusts the HUD size.
*   **Dragging**: Click and drag the **top area** of the HUD to reposition it.

---

## 3. Understanding the Metrics

*   **Remaining HP**: The last detected health of the boss.
*   **Real-time DPS**: Damage per second calculated over a short interval.
*   **Combat Time**: Time spent dealing damage.
*   **Total Damage**: HP lost by the boss since the start of monitoring.
*   **Average DPM**: Overall performance (Damage Per Minute).

---

## 4. Analytics (Outlier Protection)
The monitor includes logic to filter OCR errors:
*   **HP Jitter Filter**: If the boss's HP increases by more than 50,000, the data is ignored.
*   **Glitched Drop Filter**: If the HP drops by more than 500,000 in a single frame, it is ignored.
*   **Auto-Finish**: If the HP bar is not detected for more than 3 seconds, the app marks the combat as **FINISHED**.

---

## 5. Generating Reports
After combat, click **"GENERATE PNG REPORT"**. 
*   The app creates a graph showing the **DPS Curve**.
*   Reports are saved in the same folder as the application with the name `Boss_Report_YYYYMMDD_HHMMSS.png`.

---
*Developed for the MapleStory community.*
