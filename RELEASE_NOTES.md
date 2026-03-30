# MapleStory Boss DPM Monitor - Release Notes

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
