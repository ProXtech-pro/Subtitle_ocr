from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Sequence

LogFn = Callable[[str], None]


@dataclass(frozen=True)
class Tooling:
    tesseract_exe: Path
    mkvtoolnix_dir: Optional[Path] = None
    tessdata_prefix: Optional[Path] = None


@dataclass(frozen=True)
class OCRSettings:
    pgsrip_lang: str  # IETF code, ex: en, ro
    tess_lang: str  # Tesseract code, ex: eng, ron
    tags: Sequence[str]  # pgsrip tags
    max_workers: Optional[int] = 4
    force: bool = True
    rip_all: bool = False
    debug_verbose: bool = False
    keep_temp: bool = False


@dataclass(frozen=True)
class Paths:
    input_dir: Path
    output_dir: Path
    log_dir: Path


@dataclass(frozen=True)
class RunResult:
    success: bool
    message: str
    analysis: Dict[str, Any]
    output_srt: Optional[Path] = None
