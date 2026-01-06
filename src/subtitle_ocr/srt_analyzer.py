from __future__ import annotations

from pathlib import Path
from typing import Dict, Any
import re

def analyze_srt_file(srt_path: Path) -> Dict[str, Any]:
    """Analyze an SRT file and return a quality/content heuristic.

    This is a modularized/cleaned version of the analyzer you already had in `sup_to_srt.py`,
    kept deterministic and GUI-friendly.
    """
    analysis: Dict[str, Any] = {
        "size": 0,
        "lines": 0,
        "subtitles": 0,
        "time_sequences": 0,
        "empty_lines": 0,
        "avg_subtitle_length": 0.0,
        "duration_seconds": 0.0,  # best-effort (may remain 0.0)
        "status": "UNKNOWN",
        "has_content": False,
    }

    if not srt_path.exists():
        analysis["status"] = "MISSING ❌"
        return analysis

    # --- read file (utf-8 first, then fallback) ---
    content: str
    try:
        content = srt_path.read_text(encoding="utf-8", errors="ignore")
    except UnicodeDecodeError:
        try:
            content = srt_path.read_text(encoding="latin-1", errors="ignore")
            analysis["status"] = "LATIN-1 ENCODING"
        except Exception as e:
            analysis["status"] = f"READ ERROR: {type(e).__name__}"
            return analysis
    except Exception as e:
        analysis["status"] = f"READ ERROR: {type(e).__name__}"
        return analysis

    try:
        analysis["size"] = srt_path.stat().st_size
        if analysis["size"] == 0:
            analysis["status"] = "EMPTY ❌"
            return analysis

        lines = content.splitlines()
        analysis["lines"] = len(lines)
        analysis["empty_lines"] = sum(1 for ln in lines if not ln.strip())

        # 1) sequence counters
        seq_pattern = r"^\s*\d+\s*$"
        analysis["subtitles"] = len(re.findall(seq_pattern, content, re.MULTILINE))

        # 2) time sequences (00:00:00,000 --> 00:00:02,000)
        time_pattern = r"\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}"
        analysis["time_sequences"] = len(re.findall(time_pattern, content))

        # 3) average subtitle line length (rough)
        text_content = re.sub(seq_pattern, "", content, flags=re.MULTILINE)
        text_content = re.sub(time_pattern, "", text_content)
        text_lines = [ln.strip() for ln in text_content.splitlines() if ln.strip()]
        if text_lines:
            analysis["avg_subtitle_length"] = sum(len(ln) for ln in text_lines) / float(len(text_lines))

        analysis["has_content"] = analysis["subtitles"] > 0 and analysis["time_sequences"] > 0

        # 4) best-effort duration estimation from last timestamp
        #    NOTE: this is heuristic; we keep it conservative.
        ts_pat = r"(\d{2}):(\d{2}):(\d{2}),(\d{3})"
        ts = re.findall(ts_pat, content)
        if ts:
            hh, mm, ss, ms = ts[-1]
            analysis["duration_seconds"] = int(hh) * 3600 + int(mm) * 60 + int(ss) + (int(ms) / 1000.0)

        # --- status heuristic (ported from your implementation) ---
        if analysis["size"] < 100:
            analysis["status"] = "FOARTE MIC ⚠️"
        elif analysis["subtitles"] == 0 and analysis["time_sequences"] == 0:
            analysis["status"] = "FĂRĂ SUBS ❌"
        elif analysis["subtitles"] < 5:
            analysis["status"] = "PUȚINE SUBS ⚠️"
        elif analysis["subtitles"] < 20:
            analysis["status"] = "MEDIU ✓"
        elif analysis["subtitles"] < 50:
            analysis["status"] = "BUN ✓"
        elif analysis["subtitles"] < 100:
            analysis["status"] = "FOARTE BUN ✓"
        else:
            analysis["status"] = "EXCELENT ✓"

        # Inconsistency check between sequences and timings
        if analysis["subtitles"] > 0 and analysis["time_sequences"] > 0:
            if abs(analysis["subtitles"] - analysis["time_sequences"]) > 5:
                analysis["status"] = f"INCONSISTENT ⚠️ ({analysis['subtitles']} vs {analysis['time_sequences']})"

    except Exception as e:
        analysis["status"] = f"ANALYSIS ERROR: {type(e).__name__}"

    return analysis
