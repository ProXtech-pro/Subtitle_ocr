# Subtitle OCR Pro (PGS → SRT)

GUI-first converter for PGS/SUP subtitles embedded in video files, using **pgsrip** + **Tesseract OCR**.

## Environment (your current constraints)
- Python 3.9 is supported.
- `pgsrip` is pinned to `0.1.11` for Python 3.9 compatibility (newer versions may require Python >= 3.11).

## Quick start (Windows)

1. Install Python 3.9+
2. Install dependencies:
   ```bash
   pip install -e .
   ```
3. Create a `.env` (or copy `.env.example`) and set:
   - `INPUT_DIR`, `OUTPUT_DIR`, `LOG_DIR`
   - `TESSERACT_EXE`
   - `PGSRIP_LANG` (e.g. `en` / `ro`)
   - `TESS_LANG` (e.g. `eng` / `ron`)
   - `TESSDATA_PREFIX` (recommended: `tessdata_best` project-local)
   - `MKVTOOLNIX_DIR` (recommended default: `C:\Program Files\MKVToolNix`)

4. Place traineddata files into `./tessdata_best`:
   - `eng.traineddata`
   - `ron.traineddata`

5. Run GUI:
   ```bash
   subtitle-ocr-gui
   ```

## GUI features
- **Check setup** validates Tesseract, tessdata_best, and MKVToolNix.
- Each run stores results in-memory and shows a **Run summary** at the end.
- **Export report** exports the last run to JSON or CSV.
- GUI settings are persisted to a user config file (Windows: `%APPDATA%\subtitle-ocr-pro\settings.json`).
