from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass(frozen=True)
class Defaults:
    input_dir: Path
    output_dir: Path
    log_dir: Path
    pgsrip_lang: str
    tess_lang: str
    tesseract_exe: Path
    tessdata_prefix: Optional[Path]
    mkvtoolnix_dir: Optional[Path]


def _env_path(name: str, default: str) -> Path:
    return Path(os.getenv(name, default)).expanduser().resolve()


def project_root() -> Path:
    """Best-effort project root.

    Works well for editable installs where src/ is present.
    Fallback is current working directory.
    """
    try:
        # .../src/subtitle_ocr/config.py -> .../src -> .../(project root)
        return Path(__file__).resolve().parents[2]
    except Exception:
        return Path.cwd().resolve()


def _default_tessdata_dir(root: Path) -> Optional[Path]:
    p = (root / "tessdata_best").resolve()
    return p if p.exists() else None


def _default_mkvtoolnix_dir() -> Optional[Path]:
    p = Path(r"C:\Program Files\MKVToolNix")
    return p if p.exists() else None


def load_defaults(env_file: str | None = None) -> Defaults:
    """Load configuration defaults from .env / environment.

    Step 2 (stabilized):
    - avoid import-time fixed globals;
    - configuration is reloadable/testable.

    Additional policy:
    - MKVTOOLNIX_DIR defaults to a standard Windows install path *only if it exists*.
    - TESSDATA_PREFIX defaults to project-local ./tessdata_best *only if it exists*.
    """
    if env_file:
        load_dotenv(env_file, override=False)
    else:
        load_dotenv(override=False)

    root = project_root()

    input_dir = _env_path("INPUT_DIR", str(root / "input"))
    output_dir = _env_path("OUTPUT_DIR", str(root / "output"))
    log_dir = _env_path("LOG_DIR", str(root / "logs"))

    pgsrip_lang = os.getenv("PGSRIP_LANG", "en").strip()
    tess_lang = os.getenv("TESS_LANG", "eng").strip()

    tesseract_exe = Path(
        os.getenv("TESSERACT_EXE", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    ).expanduser()

    tessdata_raw = os.getenv("TESSDATA_PREFIX", "").strip()
    tessdata_prefix: Optional[Path]
    if tessdata_raw:
        tessdata_prefix = Path(tessdata_raw).expanduser().resolve()
    else:
        tessdata_prefix = _default_tessdata_dir(root)

    mkv_raw = os.getenv("MKVTOOLNIX_DIR", "").strip()
    mkvtoolnix_dir: Optional[Path]
    if mkv_raw:
        mkvtoolnix_dir = Path(mkv_raw).expanduser().resolve()
    else:
        mkvtoolnix_dir = _default_mkvtoolnix_dir()

    return Defaults(
        input_dir=input_dir,
        output_dir=output_dir,
        log_dir=log_dir,
        pgsrip_lang=pgsrip_lang,
        tess_lang=tess_lang,
        tesseract_exe=tesseract_exe,
        tessdata_prefix=tessdata_prefix,
        mkvtoolnix_dir=mkvtoolnix_dir,
    )


def ensure_dirs(input_dir: Path, output_dir: Path, log_dir: Path) -> None:
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
