# MapleStory Boss DPM Monitor

A GPU-accelerated combat analytics tool for MapleStory.

## Features

- **GPU-Accelerated OCR**: Uses `EasyOCR` with CUDA support for HP detection.
- **Real-Time HUD**: Transparent, borderless overlay.
- **Analytics**: Tracks DPS, DPM, Total Damage, and estimated time remaining.
- **Outlier Detection**: Filters OCR jitter and boss disappearance logic.
- **Reports**: Generates PNG charts with DPS curves.
- **UI**: Interface with Google Sans typography and High DPI support.

## Gallery

| | |
|:---:|:---:|
| ![Example 1](gallery/Screenshot%202026-03-30%20044122.png) | ![Example 2](gallery/Screenshot%202026-03-30%20045538.png) |
| ![Example 3](gallery/Screenshot%202026-03-30%20045644.png) | ![Example 4](gallery/Screenshot%202026-03-30%20045816.png) |
| ![Example 5](gallery/Screenshot%202026-03-30%20131734.png) | ![Example 6](gallery/Screenshot%202026-03-30%20131929.png) |

## Hotkeys

| Key | Action |
| :--- | :--- |
| **F7** | Toggle Monitoring (ON/OFF) |
| **F8** | Reset Session Metrics |
| **F9** | Show/Hide HUD Overlay |

## Requirements

- Python 3.10+
- NVIDIA GPU with CUDA support (recommended)
- Dependencies: `easyocr`, `torch`, `opencv-python`, `mss`, `keyboard`, `pandas`, `matplotlib`, `PIL`

## Installation

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

## Building the Executable (.exe)

To generate a standalone executable with GPU support:

1. Ensure you have an NVIDIA GPU and Python 3.10+ installed.
2. Run the provided build script:
   ```powershell
   .\build.bat
   ```
   *Note: This creates a virtual environment, installs CUDA-enabled PyTorch, and bundles the app into the `dist/` folder.*

---
*Developed for the MapleStory community.*
