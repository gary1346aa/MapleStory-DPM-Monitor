# MapleStory Boss DPM Monitor - Release Notes

## v20260401.1
Release version 20260401.1.

### Improvements
*   **Export Raw Data**: Added a dedicated button to export the full combat HP history to a `.csv` file.
*   **Precision Auto-Finish**: Combat now automatically finalizes if the HP bar is missing for 1.0 second while in the ACTIVE state.
*   **Atomic UI Sync**: Refined the display engine to ensure the Dashboard and HUD update simultaneously with perfectly matched numbers.
*   **Optimized OCR**: Switched to single-pass grayscale conversion for maximum compatibility and performance.
*   **Stable Baseline**: Implemented a fresh starting baseline for every combat session to ensure accurate first-frame DPS.

---

## v20260331.5
Release version 20260331.5.

### Improvements
*   **O(1) RT_DPS Logic**: Implemented direct pointer-based indexing for real-time DPS. This ensures zero calculation overhead and mathematically eliminates "spikes" when resuming from a pause.
*   **Smart HUD States**: Refined the transition between READY, PAUSED, and IDLE. HUD now intelligently chooses the correct state when monitoring is toggled.
*   **Atomic UI Sync**: Unified the update engine to ensure the Dashboard and HUD are always perfectly in sync with identical numbers.
*   **Unified Formatting**: All time-related fields across the entire application now strictly use the compact **MM:SS** format.
*   **Fixed Placeholders**: "Remaining Time" on the HUD now correctly defaults to **--:--** on startup.

---

## v20260331.2
Release version 20260331.2.

### Improvements
*   **Auto-Stop Logic**: Monitoring now automatically stops when the combat state reaches "FINISHED".
*   **Metric Sync**: Both the HUD and main Dashboard now synchronize final results (Time, Damage, DPM) upon boss defeat.
*   **Stability**: Fixed "Infs or NaNs" error in report generation through improved data sanitization and deduplication.
*   **UI Tuning**: Frequency slider behavior improved with explicit rounding for consistent integer snapping.
*   **Maintenance**: Entire codebase formatted with Black and comments standardized.

---

## v20260331.1
Release version 20260331.1.

### Improvements
*   **OCR Optimization**: Switched to Grayscale-only preprocessing for improved performance on CPU and entry-level GPUs.
*   **Precision Timing**: Refined combat time calculation to correctly handle the "PAUSED" state using `(last_damage_time - fight_session_start)`.
*   **UI Controls**: Frequency slider now strictly snaps to integer values (1-10 Hz).
*   **Responsiveness**: Real-time DPS calculation window reduced to 1 second for more immediate feedback.
*   **Documentation**: Added PDF version of the User Manual to the build distribution.

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

### Technical Notes
*   **Optimization**: Removed specific large CUDA DLLs to reduce package size.
*   **Fallback**: Includes CPU mode if no compatible NVIDIA GPU is detected.
