# MapleStory Boss DPM Monitor: Ultimate Pro Edition

A high-precision, GPU-accelerated combat analytics tool for MapleStory, featuring a real-time HUD overlay and detailed performance reporting.

## 🚀 Features

- **GPU-Accelerated OCR**: Utilizes `EasyOCR` with CUDA support (tested on RTX 3080) for near-instant HP detection.
- **Real-Time HUD**: Transparent, borderless overlay visible to OBS but non-intrusive for the player.
- **Dynamic Analytics**: Tracks DPS, DPM, Total Damage, and estimated time remaining.
- **Smart Outlier Detection**: Intelligent filtering of OCR jitter and boss disappearance logic.
- **Visual Reports**: Generates professional PNG performance analytics with DPS curves.
- **Premium UI**: Modern interface using **Google Sans** typography and High DPI support.

## ⌨️ Hotkeys

| Key | Action |
| :--- | :--- |
| **F7** | Toggle Monitoring (ON/OFF) |
| **F8** | Reset Session Metrics |
| **F9** | Show/Hide HUD Overlay |

## 🛠️ Requirements

- Python 3.10+
- NVIDIA GPU with CUDA support (recommended)
- Dependencies: `easyocr`, `torch`, `opencv-python`, `mss`, `keyboard`, `pandas`, `matplotlib`, `PIL`

## 📦 Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/gary1346aa/MapleStory-DPM-Monitor.git
   ```
2. Install dependencies:
   ```bash
   pip install easyocr torch torchvision torchaudio opencv-python mss keyboard pandas matplotlib pillow pygetwindow
   ```
3. Run the application:
   ```bash
   python maplestory_dps_gui.py
   ```

## 📊 DPM Color Grading

The HUD automatically color-codes your Average DPM for instant feedback:
- 🤍 **0-4M**: Standard
- 💛 **4-6M**: Elevated
- 💙 **6-8M**: Elite
- 💜 **8-10M**: Master
- 💚 **12-14M**: Grandmaster
- 💖 **14M+**: Legendary

---
*Developed for MapleStory players seeking professional-grade combat analytics.*
