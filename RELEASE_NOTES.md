# MapleStory Boss DPM Monitor v20260329.6

Release version 20260329.6.

### Changes and Additions

*   **OCR Engine**: Uses `EasyOCR` with CUDA support for HP detection.
*   **UI Scaling**: Implementation of dynamic scaling based on screen resolution and Windows scaling factors. 
*   **Font Handling**: Logic added to load the included font file at runtime.
*   **Data Processing**: Added Savitzky-Golay filtering and Cubic Spline interpolation for DPS charts.
*   **HUD**: Transparent overlay for metric display.
*   **Language**: Support for English and Traditional Chinese text.

### Technical Notes
*   **Optimization**: Removed specific large CUDA DLLs to reduce package size.
*   **Fallback**: Includes CPU mode if no compatible NVIDIA GPU is detected.

### Installation
1.  Download `MapleStory_DPM_v20260329.6.zip`.
2.  Extract the folder.
3.  Run `MapleStory_DPM_v20260329.6.exe`.
4.  See `USER_MANUAL.md` for usage details.
