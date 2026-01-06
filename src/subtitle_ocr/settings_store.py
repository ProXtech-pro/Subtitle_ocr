from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

APP_NAME = "subtitle-ocr-pro"
SETTINGS_FILE = "settings.json"

def _default_config_dir() -> Path:
    # Windows-friendly: %APPDATA%\subtitle-ocr-pro ; otherwise ~/.config/subtitle-ocr-pro
    appdata = os.getenv("APPDATA")
    if appdata:
        return Path(appdata) / APP_NAME
    return Path.home() / ".config" / APP_NAME

def settings_path(custom_dir: Optional[Path] = None) -> Path:
    base = custom_dir if custom_dir else _default_config_dir()
    base.mkdir(parents=True, exist_ok=True)
    return base / SETTINGS_FILE

@dataclass
class GUISettings:
    input_dir: str = ""
    output_dir: str = ""
    log_dir: str = ""
    pgsrip_lang: str = "en"
    tess_lang: str = "eng"
    tess_exe: str = ""
    tessdata_prefix: str = ""
    mkvtoolnix_dir: str = ""
    tags: str = "ocr tidy no-sdh no-style"
    max_workers: int = 4
    force: bool = True
    rip_all: bool = False
    debug_verbose: bool = False
    keep_temp: bool = False

def load_settings(path: Optional[Path] = None) -> GUISettings:
    p = path if path else settings_path()
    if not p.exists():
        return GUISettings()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        # Only accept known keys
        obj = GUISettings()
        for k, v in data.items():
            if hasattr(obj, k):
                setattr(obj, k, v)
        return obj
    except Exception:
        return GUISettings()

def save_settings(settings: GUISettings, path: Optional[Path] = None) -> Path:
    p = path if path else settings_path()
    p.write_text(json.dumps(asdict(settings), indent=2, ensure_ascii=False), encoding="utf-8")
    return p
