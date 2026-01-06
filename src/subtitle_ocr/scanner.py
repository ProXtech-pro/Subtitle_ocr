from __future__ import annotations
from pathlib import Path
from typing import Iterable, List, Sequence, Set

VIDEO_EXTS: Set[str] = {".mkv", ".mp4", ".m4v", ".ts"}

def scan_videos(folder: Path, exts: Sequence[str] | None = None) -> List[Path]:
    folder = folder.resolve()
    use_exts = set(e.lower() for e in (exts or VIDEO_EXTS))
    if not folder.exists():
        return []
    return sorted([p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in use_exts])
