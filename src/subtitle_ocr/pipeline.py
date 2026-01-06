from __future__ import annotations

import os
import sys
import time
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from .types import OCRSettings, Paths, Tooling, RunResult, LogFn
from .srt_analyzer import analyze_srt_file

def check_tesseract(tesseract_exe: Path, tess_lang: str, log: Optional[LogFn] = None) -> Tuple[bool, str]:
    log = log or (lambda _m: None)
    if not tesseract_exe.exists():
        return False, f"Tesseract executable not found: {tesseract_exe}"
    try:
        r = subprocess.run([str(tesseract_exe), "--list-langs"], capture_output=True, text=True, check=True)
        if tess_lang not in r.stdout:
            return True, f"WARNING: Tesseract language '{tess_lang}' not present (check TESSDATA_PREFIX)."
        return True, "Tesseract OK"
    except Exception as e:
        return False, f"Failed to run Tesseract: {type(e).__name__}: {e}"

def _snapshot_srt_files(*folders: Path) -> Dict[Path, float]:
    seen: Dict[Path, float] = {}
    for folder in folders:
        if folder and folder.exists():
            for p in folder.glob("*.srt"):
                try:
                    seen[p.resolve()] = p.stat().st_mtime
                except OSError:
                    pass
    return seen

def _find_new_srt(before: Dict[Path, float], after: Dict[Path, float]) -> List[Path]:
    new_files: List[Path] = []
    for p, mtime in after.items():
        if p not in before:
            new_files.append(p)
        elif mtime > before[p] + 0.0001:
            new_files.append(p)
    new_files.sort(key=lambda x: x.stat().st_mtime if x.exists() else 0, reverse=True)
    return new_files

def _inject_path(tooling: Tooling) -> None:
    # Inject tool folders into PATH just for this process (same approach as your scripts)
    path_parts: List[str] = []
    if tooling.mkvtoolnix_dir:
        path_parts.append(str(tooling.mkvtoolnix_dir))
    path_parts.append(str(tooling.tesseract_exe.parent))
    os.environ["PATH"] = ";".join(path_parts) + ";" + os.environ.get("PATH", "")

    if tooling.tessdata_prefix:
        os.environ["TESSDATA_PREFIX"] = str(tooling.tessdata_prefix)

def process_video(
    video_path: Path,
    *,
    paths: Paths,
    tooling: Tooling,
    settings: OCRSettings,
    log: Optional[LogFn] = None,
) -> RunResult:
    log = log or (lambda _m: None)
    paths.output_dir.mkdir(parents=True, exist_ok=True)

    _inject_path(tooling)

    target_srt = paths.output_dir / f"{video_path.stem}.{settings.pgsrip_lang}.srt"
    work_dir = video_path.parent.resolve()
    cwd = Path.cwd().resolve()

    before = _snapshot_srt_files(work_dir, cwd, paths.output_dir)

    cmd: List[str] = [
        sys.executable, "-m", "pgsrip",
        "--language", settings.pgsrip_lang,
    ]
    if settings.debug_verbose:
        cmd += ["--verbose", "--debug"]
    if settings.keep_temp:
        cmd += ["--keep-temp-files"]
    for t in settings.tags:
        cmd += ["--tag", t]
    if settings.max_workers is not None:
        cmd += ["--max-workers", str(settings.max_workers)]
    if settings.force:
        cmd += ["--force"]
    if settings.rip_all:
        cmd += ["--all"]
    cmd += [str(video_path)]

    log(f"Running: {' '.join(cmd)}")

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(work_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            encoding="utf-8",
            errors="replace",
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            if line.strip():
                log(line.rstrip())
        rc = proc.wait()
        if rc != 0:
            return RunResult(False, f"pgsrip failed (exit code {rc})", {}, None)

        time.sleep(0.5)
        after = _snapshot_srt_files(work_dir, cwd, paths.output_dir)
        candidates = _find_new_srt(before, after)
        if not candidates:
            return RunResult(False, "pgsrip finished but no new/updated .srt detected", {}, None)

        stem_prefix = video_path.stem.lower()
        preferred = [p for p in candidates if p.stem.lower().startswith(stem_prefix)]
        chosen = (preferred[0] if preferred else candidates[0]).resolve()

        # If pgsrip already wrote into output with our naming, keep it
        if chosen == target_srt.resolve():
            analysis = analyze_srt_file(chosen)
            return RunResult(True, f"SRT exists ({analysis.get('status')})", analysis, chosen)

        # Otherwise move/rename to our target
        if target_srt.exists():
            target_srt.unlink()
        shutil.move(str(chosen), str(target_srt))

        analysis = analyze_srt_file(target_srt)
        return RunResult(True, f"SRT extracted ({analysis.get('status')})", analysis, target_srt)

    except Exception as e:
        return RunResult(False, f"Unexpected error: {type(e).__name__}: {e}", {}, None)
