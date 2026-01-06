import csv
import json
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Any, Dict, List, Optional

from subtitle_ocr.config import ensure_dirs, load_defaults
from subtitle_ocr.models_downloader import download_tessdata_from_github_release
from subtitle_ocr.pipeline import check_tesseract, process_video
from subtitle_ocr.scanner import scan_videos
from subtitle_ocr.settings_store import (
    GUISettings,
    load_settings,
    save_settings,
    settings_path,
)
from subtitle_ocr.types import OCRSettings, Paths, RunResult, Tooling

TESS_TRAINEDDATA_MAP = {
    "eng": "eng.traineddata",
    "ron": "ron.traineddata",
    "ita": "ita.traineddata",
}
GITHUB_OWNER = "ProXtech-pro"
GITHUB_REPO = "Subtitle_ocr"
GITHUB_ASSET_NAME = "tessdata_best_min.zip"


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Subtitle OCR Pro (PGS → SRT)")
        self.root.geometry("1100x860")

        defaults = load_defaults()
        ensure_dirs(defaults.input_dir, defaults.output_dir, defaults.log_dir)

        persisted = load_settings()

        self.input_dir = tk.StringVar(
            value=persisted.input_dir or str(defaults.input_dir)
        )
        self.output_dir = tk.StringVar(
            value=persisted.output_dir or str(defaults.output_dir)
        )
        self.log_dir = tk.StringVar(value=persisted.log_dir or str(defaults.log_dir))

        self.pgsrip_lang = tk.StringVar(
            value=persisted.pgsrip_lang or defaults.pgsrip_lang
        )
        self.tess_lang = tk.StringVar(value=persisted.tess_lang or defaults.tess_lang)
        self.tessdata_prefix = tk.StringVar(
            value=persisted.tessdata_prefix or str(defaults.tessdata_prefix or "")
        )
        self.mkv_dir = tk.StringVar(
            value=persisted.mkvtoolnix_dir or str(defaults.mkvtoolnix_dir or "")
        )
        self.tess_exe = tk.StringVar(
            value=persisted.tess_exe or str(defaults.tesseract_exe)
        )

        self.tags_var = tk.StringVar(value=persisted.tags or "ocr tidy no-sdh no-style")
        self.max_workers = tk.IntVar(value=int(persisted.max_workers or 4))
        self.force = tk.BooleanVar(value=bool(persisted.force))
        self.rip_all = tk.BooleanVar(value=bool(persisted.rip_all))
        self.debug_verbose = tk.BooleanVar(value=bool(persisted.debug_verbose))
        self.keep_temp = tk.BooleanVar(value=bool(persisted.keep_temp))

        self.all_files: List[Path] = []
        self.processing = False
        self.stop_requested = False
        self._run_results: List[Dict[str, Any]] = []

        self._build()

    def _current_gui_settings(self) -> GUISettings:
        return GUISettings(
            input_dir=self.input_dir.get(),
            output_dir=self.output_dir.get(),
            log_dir=self.log_dir.get(),
            pgsrip_lang=self.pgsrip_lang.get(),
            tess_lang=self.tess_lang.get(),
            tess_exe=self.tess_exe.get(),
            tessdata_prefix=self.tessdata_prefix.get(),
            mkvtoolnix_dir=self.mkv_dir.get(),
            tags=self.tags_var.get(),
            max_workers=int(self.max_workers.get()),
            force=bool(self.force.get()),
            rip_all=bool(self.rip_all.get()),
            debug_verbose=bool(self.debug_verbose.get()),
            keep_temp=bool(self.keep_temp.get()),
        )

    def _save_settings_now(self) -> None:
        p = save_settings(self._current_gui_settings())
        self._log(f"Saved settings to: {p}")

    def _build(self) -> None:
        main = ttk.Frame(self.root, padding=10)
        main.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)

        dir_frame = ttk.LabelFrame(main, text="Folders", padding=10)
        dir_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        dir_frame.columnconfigure(1, weight=1)

        ttk.Label(dir_frame, text="Input:").grid(row=0, column=0, sticky="w")
        ttk.Entry(dir_frame, textvariable=self.input_dir).grid(
            row=0, column=1, sticky="ew", padx=6
        )
        ttk.Button(dir_frame, text="Browse", command=self._browse_input).grid(
            row=0, column=2, padx=4
        )
        ttk.Button(dir_frame, text="Scan", command=self.scan).grid(
            row=0, column=3, padx=4
        )

        ttk.Label(dir_frame, text="Output:").grid(
            row=1, column=0, sticky="w", pady=(6, 0)
        )
        ttk.Entry(dir_frame, textvariable=self.output_dir).grid(
            row=1, column=1, sticky="ew", padx=6, pady=(6, 0)
        )
        ttk.Button(dir_frame, text="Browse", command=self._browse_output).grid(
            row=1, column=2, padx=4, pady=(6, 0)
        )
        ttk.Button(
            dir_frame,
            text="Output=Input",
            command=lambda: self.output_dir.set(self.input_dir.get()),
        ).grid(row=1, column=3, padx=4, pady=(6, 0))

        ttk.Label(dir_frame, text="Logs:").grid(
            row=2, column=0, sticky="w", pady=(6, 0)
        )
        ttk.Entry(dir_frame, textvariable=self.log_dir).grid(
            row=2, column=1, sticky="ew", padx=6, pady=(6, 0)
        )
        ttk.Button(dir_frame, text="Browse", command=self._browse_logs).grid(
            row=2, column=2, padx=4, pady=(6, 0)
        )

        files_frame = ttk.LabelFrame(main, text="Video files", padding=10)
        files_frame.grid(row=1, column=0, columnspan=3, sticky="nsew", pady=(0, 10))
        main.rowconfigure(1, weight=1)
        files_frame.columnconfigure(0, weight=1)
        files_frame.rowconfigure(0, weight=1)

        self.listbox = tk.Listbox(
            files_frame, selectmode=tk.EXTENDED, font=("Consolas", 10)
        )
        self.listbox.grid(row=0, column=0, sticky="nsew")
        sb = ttk.Scrollbar(files_frame, orient="vertical", command=self.listbox.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.listbox.configure(yscrollcommand=sb.set)

        btns = ttk.Frame(files_frame)
        btns.grid(row=0, column=2, sticky="n", padx=(10, 0))
        ttk.Button(
            btns,
            text="Select all",
            command=lambda: self.listbox.selection_set(0, tk.END),
            width=18,
        ).grid(row=0, column=0, pady=2)
        ttk.Button(
            btns,
            text="Deselect",
            command=lambda: self.listbox.selection_clear(0, tk.END),
            width=18,
        ).grid(row=1, column=0, pady=2)
        ttk.Button(
            btns, text="Remove selected", command=self.remove_selected, width=18
        ).grid(row=2, column=0, pady=(10, 2))
        ttk.Button(btns, text="Clear", command=self.clear_files, width=18).grid(
            row=3, column=0, pady=2
        )

        opt = ttk.LabelFrame(main, text="Options", padding=10)
        opt.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        opt.columnconfigure(3, weight=1)

        ttk.Label(opt, text="PGSRIP_LANG:").grid(row=0, column=0, sticky="w")
        ttk.Entry(opt, textvariable=self.pgsrip_lang, width=10).grid(
            row=0, column=1, sticky="w", padx=6
        )
        ttk.Label(opt, text="TESS_LANG:").grid(row=0, column=2, sticky="w")
        ttk.Entry(opt, textvariable=self.tess_lang, width=10).grid(
            row=0, column=3, sticky="w", padx=6
        )

        ttk.Label(opt, text="Tags:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(opt, textvariable=self.tags_var).grid(
            row=1, column=1, columnspan=3, sticky="ew", padx=6, pady=(6, 0)
        )

        ttk.Label(opt, text="Max workers:").grid(
            row=2, column=0, sticky="w", pady=(6, 0)
        )
        ttk.Spinbox(opt, from_=1, to=64, textvariable=self.max_workers, width=8).grid(
            row=2, column=1, sticky="w", padx=6, pady=(6, 0)
        )
        ttk.Checkbutton(opt, text="Force overwrite", variable=self.force).grid(
            row=2, column=2, sticky="w", pady=(6, 0)
        )
        ttk.Checkbutton(opt, text="Rip all tracks", variable=self.rip_all).grid(
            row=2, column=3, sticky="w", pady=(6, 0)
        )

        ttk.Checkbutton(opt, text="Debug verbose", variable=self.debug_verbose).grid(
            row=3, column=0, sticky="w", pady=(6, 0)
        )
        ttk.Checkbutton(opt, text="Keep temp files", variable=self.keep_temp).grid(
            row=3, column=1, sticky="w", pady=(6, 0)
        )

        ttk.Label(opt, text="tesseract.exe:").grid(
            row=4, column=0, sticky="w", pady=(6, 0)
        )
        ttk.Entry(opt, textvariable=self.tess_exe).grid(
            row=4, column=1, columnspan=3, sticky="ew", padx=6, pady=(6, 0)
        )

        ttk.Label(opt, text="TESSDATA_PREFIX:").grid(
            row=5, column=0, sticky="w", pady=(6, 0)
        )
        ttk.Entry(opt, textvariable=self.tessdata_prefix).grid(
            row=5, column=1, columnspan=3, sticky="ew", padx=6, pady=(6, 0)
        )

        ttk.Label(opt, text="MKVToolNix dir:").grid(
            row=6, column=0, sticky="w", pady=(6, 0)
        )
        ttk.Entry(opt, textvariable=self.mkv_dir).grid(
            row=6, column=1, columnspan=3, sticky="ew", padx=6, pady=(6, 0)
        )

        ctrl = ttk.Frame(main)
        ctrl.grid(row=3, column=0, columnspan=3, sticky="ew")

        self.start_btn = ttk.Button(ctrl, text="Start", command=self.start)
        self.start_btn.grid(row=0, column=0, padx=(0, 6))

        self.stop_btn = ttk.Button(
            ctrl, text="Stop", command=self.stop, state="disabled"
        )
        self.stop_btn.grid(row=0, column=1, padx=(0, 6))

        ttk.Button(ctrl, text="Check setup", command=self.check_setup).grid(
            row=0, column=2, padx=(0, 6)
        )
        ttk.Button(ctrl, text="Summary", command=self.show_summary).grid(
            row=0, column=3, padx=(0, 6)
        )
        ttk.Button(ctrl, text="Export report", command=self.export_report).grid(
            row=0, column=4, padx=(0, 6)
        )
        ttk.Button(ctrl, text="Download models", command=self.download_models).grid(
            row=0, column=5, padx=(0, 6)
        )

        self.progress = ttk.Progressbar(ctrl, maximum=100, length=420)
        self.progress.grid(row=0, column=6, sticky="ew", padx=(10, 0))
        ctrl.columnconfigure(6, weight=1)

        log_frame = ttk.LabelFrame(main, text="Log", padding=10)
        log_frame.grid(row=4, column=0, columnspan=3, sticky="nsew", pady=(10, 0))
        main.rowconfigure(4, weight=1)
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        self.log = scrolledtext.ScrolledText(
            log_frame, height=12, state="disabled", font=("Consolas", 9)
        )
        self.log.grid(row=0, column=0, sticky="nsew")

        footer = ttk.Frame(main)
        footer.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        ttk.Label(footer, text=f"Settings: {settings_path()}").grid(
            row=0, column=0, sticky="w"
        )

    def _log(self, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.log.configure(state="normal")
        self.log.insert(tk.END, f"[{ts}] {msg}\n")
        self.log.see(tk.END)
        self.log.configure(state="disabled")
        self.root.update_idletasks()

    def _browse_input(self) -> None:
        p = filedialog.askdirectory()
        if p:
            self.input_dir.set(p)
            self._save_settings_now()

    def _browse_output(self) -> None:
        p = filedialog.askdirectory()
        if p:
            self.output_dir.set(p)
            self._save_settings_now()

    def _browse_logs(self) -> None:
        p = filedialog.askdirectory()
        if p:
            self.log_dir.set(p)
            self._save_settings_now()

    def scan(self) -> None:
        folder = Path(self.input_dir.get()).resolve()
        self.all_files = scan_videos(folder)
        self.listbox.delete(0, tk.END)
        for p in self.all_files:
            try:
                size_mb = p.stat().st_size / (1024 * 1024)
                self.listbox.insert(tk.END, f"{p.name} ({size_mb:.1f} MB)")
            except OSError:
                self.listbox.insert(tk.END, f"{p.name}")
        self._log(f"Found {len(self.all_files)} video file(s).")
        self._save_settings_now()

    def clear_files(self) -> None:
        self.all_files = []
        self.listbox.delete(0, tk.END)

    def remove_selected(self) -> None:
        idxs = list(self.listbox.curselection())
        if not idxs:
            return
        for i in sorted(idxs, reverse=True):
            self.all_files.pop(i)
            self.listbox.delete(i)

    def _current_paths_tooling_settings(self):
        paths = Paths(
            input_dir=Path(self.input_dir.get()).resolve(),
            output_dir=Path(self.output_dir.get()).resolve(),
            log_dir=Path(self.log_dir.get()).resolve(),
        )
        tooling = Tooling(
            tesseract_exe=Path(self.tess_exe.get()).expanduser(),
            mkvtoolnix_dir=(
                Path(self.mkv_dir.get()).expanduser()
                if self.mkv_dir.get().strip()
                else None
            ),
            tessdata_prefix=(
                Path(self.tessdata_prefix.get()).expanduser()
                if self.tessdata_prefix.get().strip()
                else None
            ),
        )
        tags = [t for t in self.tags_var.get().split() if t.strip()]
        settings = OCRSettings(
            pgsrip_lang=self.pgsrip_lang.get().strip(),
            tess_lang=self.tess_lang.get().strip(),
            tags=tags,
            max_workers=int(self.max_workers.get()),
            force=bool(self.force.get()),
            rip_all=bool(self.rip_all.get()),
            debug_verbose=bool(self.debug_verbose.get()),
            keep_temp=bool(self.keep_temp.get()),
        )
        return paths, tooling, settings

    def _validate_mkvtoolnix(self, mkv_dir: Optional[Path]) -> Optional[str]:
        if not mkv_dir:
            return (
                "MKVTOOLNIX_DIR is empty. Expected a folder that contains "
                "mkvmerge.exe / mkvextract.exe.\n"
                "Set MKVTOOLNIX_DIR in .env or in the GUI."
            )
        if not mkv_dir.exists():
            return f"MKVToolNix folder does not exist: {mkv_dir}"
        mkvmerge = mkv_dir / "mkvmerge.exe"
        mkvextract = mkv_dir / "mkvextract.exe"
        if not mkvmerge.exists() and not mkvextract.exists():
            return (
                f"MKVToolNix folder looks invalid: {mkv_dir}\n"
                "Expected mkvmerge.exe and/or mkvextract.exe inside that directory."
            )
        return None

    def _validate_tessdata(
        self, tessdata: Optional[Path], tess_lang: str
    ) -> Optional[str]:
        if not tessdata:
            return (
                "TESSDATA_PREFIX is empty.\n"
                "Set TESSDATA_PREFIX=tessdata_best (project-local) and place "
                "traineddata files there."
            )
        if not tessdata.exists():
            return f"TESSDATA_PREFIX folder does not exist: {tessdata}"
        lang_code = tess_lang.strip()
        required = TESS_TRAINEDDATA_MAP.get(
            lang_code,
            f"{lang_code}.traineddata",
        )
        if not (tessdata / required).exists():
            msg = (
                f"Missing traineddata for TESS_LANG='{tess_lang}': "
                f"expected {required} in\n"
                f"{tessdata}\n"
                "Place the traineddata file(s) into the project-local "
                "tessdata_best folder."
            )
            return msg
        return None

    def check_setup(self) -> None:
        _paths, tooling, settings = self._current_paths_tooling_settings()

        ok, tmsg = check_tesseract(
            tooling.tesseract_exe, settings.tess_lang, log=self._log
        )
        problems = []
        if not ok:
            problems.append(tmsg)

        mkv_problem = self._validate_mkvtoolnix(tooling.mkvtoolnix_dir)
        if mkv_problem:
            problems.append(mkv_problem)

        tess_problem = self._validate_tessdata(
            tooling.tessdata_prefix, settings.tess_lang
        )
        if tess_problem:
            problems.append(tess_problem)

        if problems:
            messagebox.showerror("Setup problems", "\n\n".join(problems))
        else:
            messagebox.showinfo("Setup OK", "All required tools/data look OK.")

        self._save_settings_now()

    def download_models(self) -> None:
        """
        Download tessdata_best traineddata files from GitHub Releases (latest),
        and place them into project-local ./tessdata_best
        """
        dest_dir = (
            Path(self.tessdata_prefix.get()).resolve()
            if self.tessdata_prefix.get().strip()
            else (Path.cwd() / "tessdata_best")
        )
        dest_dir.mkdir(parents=True, exist_ok=True)

        def worker():
            self._log("Starting model download from GitHub Releases...")
            ok, msg = download_tessdata_from_github_release(
                owner=GITHUB_OWNER,
                repo=GITHUB_REPO,
                asset_name=GITHUB_ASSET_NAME,
                dest_dir=dest_dir,
                log=self._log,
            )
            if ok:
                self._log(msg)
                messagebox.showinfo("Download models", msg)
            else:
                self._log("ERROR: " + msg)
                messagebox.showerror("Download models failed", msg)

        threading.Thread(target=worker, daemon=True).start()

    def _record_result(self, video: Path, res: RunResult) -> None:
        self._run_results.append(
            {
                "video": str(video),
                "success": bool(res.success),
                "message": res.message,
                "analysis": res.analysis or {},
                "output_srt": str(res.output_srt) if res.output_srt else "",
            }
        )

    def show_summary(self) -> None:
        if not self._run_results:
            messagebox.showinfo("Summary", "No run results yet.")
            return

        total = len(self._run_results)
        succ = sum(1 for r in self._run_results if r.get("success"))
        fail = total - succ

        failures = [r for r in self._run_results if not r.get("success")]
        lines: List[str] = []
        lines.append(f"Total: {total}")
        lines.append(f"Success: {succ}")
        lines.append(f"Failed: {fail}")
        lines.append("")
        if failures:
            lines.append("Failures:")
            for r in failures[:10]:
                v = Path(r["video"]).name
                lines.append(f"- {v}: {r.get('message')}")
            if len(failures) > 10:
                lines.append(f"... and {len(failures) - 10} more")
        else:
            lines.append("No failures.")

        messagebox.showinfo("Run summary", "\n".join(lines))

    def export_report(self) -> None:
        if not self._run_results:
            messagebox.showwarning("Export", "No run results to export yet.")
            return

        default_name = f"subtitle_ocr_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfile=default_name + ".json",
            filetypes=[("JSON", "*.json"), ("CSV", "*.csv")],
            title="Export report",
        )
        if not path:
            return

        out = Path(path)
        try:
            if out.suffix.lower() == ".csv":
                self._export_csv(out)
            else:
                self._export_json(out)
            messagebox.showinfo("Export", f"Report exported to:\n{out}")
            self._log(f"Exported report: {out}")
        except Exception as e:
            messagebox.showerror("Export failed", f"{type(e).__name__}: {e}")

    def _export_json(self, out: Path) -> None:
        payload = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "results": self._run_results,
        }
        out.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def _export_csv(self, out: Path) -> None:
        fieldnames = [
            "video",
            "success",
            "message",
            "output_srt",
            "status",
            "size",
            "lines",
            "subtitles",
            "time_sequences",
            "empty_lines",
            "avg_subtitle_length",
            "duration_seconds",
        ]
        with out.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in self._run_results:
                a = r.get("analysis") or {}
                row = {
                    "video": r.get("video", ""),
                    "success": r.get("success", False),
                    "message": r.get("message", ""),
                    "output_srt": r.get("output_srt", ""),
                    "status": a.get("status", ""),
                    "size": a.get("size", ""),
                    "lines": a.get("lines", ""),
                    "subtitles": a.get("subtitles", ""),
                    "time_sequences": a.get("time_sequences", ""),
                    "empty_lines": a.get("empty_lines", ""),
                    "avg_subtitle_length": a.get("avg_subtitle_length", ""),
                    "duration_seconds": a.get("duration_seconds", ""),
                }
                w.writerow(row)

    def start(self) -> None:
        if self.processing:
            return
        if not self.all_files:
            messagebox.showwarning(
                "No files", "No video files to process. Click Scan first."
            )
            return

        paths, tooling, settings = self._current_paths_tooling_settings()
        ensure_dirs(paths.input_dir, paths.output_dir, paths.log_dir)

        mkv_problem = self._validate_mkvtoolnix(tooling.mkvtoolnix_dir)
        tess_problem = self._validate_tessdata(
            tooling.tessdata_prefix, settings.tess_lang
        )
        if mkv_problem or tess_problem:
            problems = [p for p in (mkv_problem, tess_problem) if p]
            messagebox.showerror("Cannot start", "\n\n".join(problems))
            return

        self._save_settings_now()
        self._run_results = []

        self.processing = True
        self.stop_requested = False
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.progress["value"] = 0

        def worker():
            total = len(self.all_files)
            ok_count = 0

            for i, vp in enumerate(self.all_files, start=1):
                if self.stop_requested:
                    self._log("Stop requested.")
                    break

                self._log(f"=== [{i}/{total}] {vp.name} ===")
                res = process_video(
                    vp, paths=paths, tooling=tooling, settings=settings, log=self._log
                )
                self._record_result(vp, res)

                self._log(f"Result: {'OK' if res.success else 'FAIL'} | {res.message}")
                if res.output_srt:
                    self._log(f"Output: {res.output_srt}")
                if res.analysis:
                    self._log(f"Analysis: {res.analysis}")

                if res.success:
                    ok_count += 1

                self.progress["value"] = (i / total) * 100

            self._log(f"Done: {ok_count}/{total} succeeded.")
            self.processing = False
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            self.root.after(100, self.show_summary)

        threading.Thread(target=worker, daemon=True).start()

    def stop(self) -> None:
        if self.processing:
            self.stop_requested = True
            self.stop_btn.configure(state="disabled")


def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
