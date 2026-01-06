from __future__ import annotations

import argparse
from pathlib import Path

from subtitle_ocr.config import ensure_dirs, load_defaults
from subtitle_ocr.pipeline import check_tesseract, process_video
from subtitle_ocr.scanner import scan_videos
from subtitle_ocr.types import OCRSettings, Paths, Tooling


def main() -> int:
    d = load_defaults()

    parser = argparse.ArgumentParser(
        description="Subtitle OCR (PGS→SRT) - CLI (optional)"
    )
    parser.add_argument("--input", default=str(d.input_dir))
    parser.add_argument("--output", default=str(d.output_dir))
    parser.add_argument("--logs", default=str(d.log_dir))
    parser.add_argument("--pgsrip-lang", default=d.pgsrip_lang)
    parser.add_argument("--tess-lang", default=d.tess_lang)
    parser.add_argument("--tesseract-exe", default=str(d.tesseract_exe))
    parser.add_argument("--tessdata-prefix", default=str(d.tessdata_prefix or ""))
    parser.add_argument("--mkvtoolnix-dir", default=str(d.mkvtoolnix_dir or ""))
    parser.add_argument("--tags", default="ocr tidy no-sdh no-style")
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--force", action="store_true", default=True)
    parser.add_argument("--rip-all", action="store_true", default=False)
    parser.add_argument("--debug-verbose", action="store_true", default=False)
    parser.add_argument("--keep-temp", action="store_true", default=False)
    args = parser.parse_args()

    paths = Paths(
        Path(args.input).resolve(),
        Path(args.output).resolve(),
        Path(args.logs).resolve(),
    )
    ensure_dirs(paths.input_dir, paths.output_dir, paths.log_dir)

    tooling = Tooling(
        tesseract_exe=Path(args.tesseract_exe),
        tessdata_prefix=Path(args.tessdata_prefix) if args.tessdata_prefix else None,
        mkvtoolnix_dir=Path(args.mkvtoolnix_dir) if args.mkvtoolnix_dir else None,
    )
    settings = OCRSettings(
        pgsrip_lang=args.pgsrip_lang,
        tess_lang=args.tess_lang,
        tags=[t for t in args.tags.split() if t.strip()],
        max_workers=args.max_workers,
        force=args.force,
        rip_all=args.rip_all,
        debug_verbose=args.debug_verbose,
        keep_temp=args.keep_temp,
    )

    ok, msg = check_tesseract(tooling.tesseract_exe, settings.tess_lang)
    print(msg)
    if not ok:
        return 2

    videos = scan_videos(paths.input_dir)
    if not videos:
        print(f"No videos found in {paths.input_dir}")
        return 0

    succ = 0
    for v in videos:
        res = process_video(
            v, paths=paths, tooling=tooling, settings=settings, log=print
        )
        succ += 1 if res.success else 0
    print(f"Done: {succ}/{len(videos)} succeeded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
