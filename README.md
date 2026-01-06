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
## Models (tessdata_best)

This project does not ship Tesseract traineddata files in the git repository.

### Option A (manual)
1. Go to GitHub Releases (Latest)
2. Download `tessdata_best_min.zip`
3. Extract into `./tessdata_best/` so you have:
   - `tessdata_best/eng.traineddata`
   - `tessdata_best/ron.traineddata`

### Option B (GUI)
Open the GUI and click **Download models**.

## GUI features
- **Check setup** validates Tesseract, tessdata_best, and MKVToolNix.
- Each run stores results in-memory and shows a **Run summary** at the end.
- **Export report** exports the last run to JSON or CSV.
- GUI settings are persisted to a user config file (Windows: `%APPDATA%\subtitle-ocr-pro\settings.json`).

### Tesseract OCR (required)

Subtitle OCR Pro requires **Tesseract OCR** for subtitle image recognition.

#### Recommended (official Windows builds – actively maintained)
Download the official Windows installers from UB Mannheim:
https://github.com/UB-Mannheim/tesseract/wiki

This project is tested with **Tesseract 4.x and 5.x**.

Default installation path:
C:\Program Files\Tesseract-OCR\tesseract.exe

#### Alternative (verified mirror – same official builds)
The same Tesseract 5.x Windows installers are also available via SourceForge:
https://sourceforge.net/projects/tesseract-ocr.mirror/files/5.5.0/tesseract-ocr-w64-setup-5.5.0.20241111.exe/download

This mirror hosts the **official UB Mannheim builds**, not legacy versions.

#### Legacy versions (NOT recommended)
Older Tesseract versions (e.g. 3.x) can be found on SourceForge, but are not recommended:
https://deac-riga.dl.sourceforge.net/project/tesseract-ocr-alt/tesseract-ocr-setup-3.02.02.exe

⚠️ Legacy versions have significantly worse OCR quality and compatibility.

#### Configuration
- Set the full path to `tesseract.exe` in the GUI, or
- Define it in a `.env` file:
  TESSERACT_EXE=C:\Program Files\Tesseract-OCR\tesseract.exe
