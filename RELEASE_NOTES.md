# MapleStory Boss DPM Monitor - Release Notes

## v20260401.3
Release version 20260401.3.

### Improvements
*   **Export Raw Data**: Added a dedicated button to export the full combat HP history to a `.csv` file.
*   **Smart Auto-Finish**: Combat now automatically finalizes exactly 1.0 second after the HP bar disappears while in the ACTIVE state.
*   **Atomic UI Sync**: Refined the display engine to ensure the Dashboard and HUD update simultaneously with perfectly matched numbers.
*   **O(1) RT_DPS Logic**: Implemented direct pointer-based indexing for real-time DPS, ensuring zero calculation overhead and spike-free resumes.
*   **Unified Formatting**: All time-related fields across the entire application now strictly use the compact **MM:SS** format.
*   **Zero-Install Typography**: Google Sans font is now dynamically loaded into memory at runtime—no installation required.

---

## v20260331.5
Release version 20260331.5.

### Improvements
*   **O(1) RT_DPS Logic**: Initial implementation of direct pointer-based indexing for real-time DPS.
*   **Smart HUD States**: Refined the transition between READY, PAUSED, and IDLE.
*   **Unified Formatting**: Initial rollout of compact MM:SS time format.

---

## v20260329.6
Release version 20260329.6.

### Changes and Additions
*   **OCR Engine**: Uses `EasyOCR` with CUDA support for HP detection.
*   **UI Scaling**: Implementation of dynamic scaling based on screen resolution and Windows scaling factors. 
*   **Font Handling**: Logic added to load the included font file at runtime.
*   **Data Processing**: Added Savitzky-Golay filtering and Cubic Spline interpolation for DPS charts.
*   **HUD**: Transparent overlay for metric display.
*   **Language**: Support for English and Traditional Chinese text.
