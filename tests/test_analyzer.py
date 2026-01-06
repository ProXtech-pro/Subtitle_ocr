from pathlib import Path

from subtitle_ocr.srt_analyzer import analyze_srt_file


def test_missing_file():
    res = analyze_srt_file(Path("this_file_should_not_exist.srt"))
    assert (
        res["status"] in ("MISSING", "EMPTY", "UNKNOWN", "ERROR: FileNotFoundError")
        or res["size"] == 0
    )
