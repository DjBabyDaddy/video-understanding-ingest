#!/usr/bin/env python3
"""Desktop tool window for video-understanding-ingest."""

from __future__ import annotations

import queue
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
OUTPUTS_DIR = DATA_DIR / "outputs"
REPO_ROOT = ROOT.parent
SKILL_DIR = Path(os.environ.get("VIDEO_INGEST_SKILL_DIR", REPO_ROOT / "skill" / "video-understanding-ingest")).expanduser()
INGEST_SCRIPT = SKILL_DIR / "scripts" / "video_ingest.py"
DIGEST_SCRIPT = SKILL_DIR / "scripts" / "video_digest.py"
DEFAULT_VAULT = Path(os.environ.get("VIDEO_LEARNING_VAULT", Path.home() / "Video-Learning-Vault")).expanduser()


class VideoTool(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Video Understanding")
        self.geometry("900x680")
        self.minsize(760, 560)

        self.selected_file = tk.StringVar()
        self.url = tk.StringVar()
        self.frame_mode = tk.StringVar(value="sample")
        self.fps = tk.StringVar(value="1")
        self.transcribe = tk.StringVar(value="auto")
        self.ocr = tk.StringVar(value="auto")
        self.url_mode = tk.StringVar(value="auto")
        self.memory_mode = tk.BooleanVar(value=True)
        self.title_value = tk.StringVar()
        self.creator_value = tk.StringVar()
        self.status = tk.StringVar(value="Ready")
        self.output_dir: Path | None = None
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.running = False

        self.configure(background="#f5f7f8")
        self.build_ui()
        self.after(200, self.drain_log_queue)
        self.refresh_deps()

    def build_ui(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#f5f7f8")
        style.configure("Panel.TFrame", background="#ffffff", borderwidth=1, relief="solid")
        style.configure("TLabel", background="#f5f7f8", foreground="#1e2528")
        style.configure("Panel.TLabel", background="#ffffff", foreground="#1e2528")
        style.configure("Muted.TLabel", background="#ffffff", foreground="#5e6a70")
        style.configure("TButton", padding=8)

        outer = ttk.Frame(self, padding=18)
        outer.pack(fill="both", expand=True)

        title = ttk.Label(outer, text="Video Understanding", font=("Segoe UI", 20, "bold"))
        title.pack(anchor="w")
        subtitle = ttk.Label(
            outer,
            text="Choose a video file or paste a public URL. Results are saved locally.",
            foreground="#5e6a70",
        )
        subtitle.pack(anchor="w", pady=(4, 14))

        top = ttk.Frame(outer)
        top.pack(fill="x")

        input_panel = ttk.Frame(top, style="Panel.TFrame", padding=14)
        input_panel.pack(side="left", fill="both", expand=True, padx=(0, 12))

        ttk.Label(input_panel, text="Video file", style="Panel.TLabel").pack(anchor="w")
        file_row = ttk.Frame(input_panel, style="Panel.TFrame")
        file_row.pack(fill="x", pady=(6, 12))
        ttk.Entry(file_row, textvariable=self.selected_file).pack(side="left", fill="x", expand=True)
        ttk.Button(file_row, text="Browse", command=self.choose_file).pack(side="left", padx=(8, 0))

        ttk.Label(input_panel, text="Public URL", style="Panel.TLabel").pack(anchor="w")
        ttk.Entry(input_panel, textvariable=self.url).pack(fill="x", pady=(6, 12))

        memory_row = ttk.Frame(input_panel, style="Panel.TFrame")
        memory_row.pack(fill="x", pady=(0, 10))
        ttk.Checkbutton(memory_row, text="Save only Obsidian learning digest by default", variable=self.memory_mode).pack(anchor="w")

        ttk.Label(input_panel, text="Optional title", style="Panel.TLabel").pack(anchor="w")
        ttk.Entry(input_panel, textvariable=self.title_value).pack(fill="x", pady=(6, 10))
        ttk.Label(input_panel, text="Optional creator", style="Panel.TLabel").pack(anchor="w")
        ttk.Entry(input_panel, textvariable=self.creator_value).pack(fill="x", pady=(6, 12))

        opts = ttk.Frame(input_panel, style="Panel.TFrame")
        opts.pack(fill="x")
        self.add_option(opts, "Depth", self.frame_mode, ["sample", "key", "all", "none"], 0, 0)
        self.add_option(opts, "FPS", self.fps, None, 0, 1)
        self.add_option(opts, "Transcript", self.transcribe, ["auto", "openai", "whisper", "none"], 1, 0)
        self.add_option(opts, "OCR", self.ocr, ["auto", "tesseract", "none"], 1, 1)
        self.add_option(opts, "URL mode", self.url_mode, ["auto", "direct", "yt-dlp"], 2, 0)

        action_row = ttk.Frame(input_panel, style="Panel.TFrame")
        action_row.pack(fill="x", pady=(14, 0))
        ttk.Button(action_row, text="Analyze File", command=self.analyze_file).pack(side="left")
        ttk.Button(action_row, text="Analyze URL", command=self.analyze_url).pack(side="left", padx=(8, 0))
        ttk.Button(action_row, text="Open Output", command=self.open_output).pack(side="left", padx=(8, 0))

        deps_panel = ttk.Frame(top, style="Panel.TFrame", padding=14)
        deps_panel.pack(side="left", fill="both", expand=True)
        ttk.Label(deps_panel, text="Runtime check", style="Panel.TLabel", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        ttk.Button(deps_panel, text="Refresh", command=self.refresh_deps).pack(anchor="e", pady=(0, 6))
        self.deps_text = tk.Text(deps_panel, height=12, wrap="word", borderwidth=0, background="#ffffff")
        self.deps_text.pack(fill="both", expand=True)

        status_row = ttk.Frame(outer)
        status_row.pack(fill="x", pady=(14, 8))
        ttk.Label(status_row, textvariable=self.status, foreground="#0f766e").pack(anchor="w")

        log_panel = ttk.Frame(outer, style="Panel.TFrame", padding=14)
        log_panel.pack(fill="both", expand=True)
        ttk.Label(log_panel, text="Job log", style="Panel.TLabel", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.log_text = tk.Text(log_panel, wrap="word", borderwidth=0, background="#ffffff")
        self.log_text.pack(fill="both", expand=True, pady=(8, 0))

    def add_option(self, parent: ttk.Frame, label: str, var: tk.StringVar, values: list[str] | None, row: int, col: int) -> None:
        cell = ttk.Frame(parent, style="Panel.TFrame")
        cell.grid(row=row, column=col, sticky="ew", padx=(0 if col == 0 else 8, 0), pady=(0, 8))
        parent.columnconfigure(col, weight=1)
        ttk.Label(cell, text=label, style="Muted.TLabel").pack(anchor="w")
        if values:
            ttk.Combobox(cell, textvariable=var, values=values, state="readonly").pack(fill="x", pady=(4, 0))
        else:
            ttk.Entry(cell, textvariable=var).pack(fill="x", pady=(4, 0))

    def choose_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose video",
            filetypes=[
                ("Video files", "*.mp4 *.mov *.m4v *.webm *.mkv *.avi *.mpeg *.mpg *.wmv"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.selected_file.set(path)

    def base_command(self, source: str, out_dir: Path) -> list[str]:
        if self.memory_mode.get():
            command = [
                sys.executable,
                str(DIGEST_SCRIPT),
                source,
                "--url-mode",
                self.url_mode.get(),
                "--frame-mode",
                self.frame_mode.get(),
                "--fps",
                self.fps.get(),
                "--transcribe",
                self.transcribe.get(),
                "--ocr",
                self.ocr.get(),
            ]
            if self.title_value.get().strip():
                command.extend(["--title", self.title_value.get().strip()])
            if self.creator_value.get().strip():
                command.extend(["--creator", self.creator_value.get().strip()])
            return command

        return [
            sys.executable,
            str(INGEST_SCRIPT),
            source,
            "--output-dir",
            str(out_dir),
            "--url-mode",
            self.url_mode.get(),
            "--frame-mode",
            self.frame_mode.get(),
            "--fps",
            self.fps.get(),
            "--transcribe",
            self.transcribe.get(),
            "--ocr",
            self.ocr.get(),
        ]

    def analyze_file(self) -> None:
        source = self.selected_file.get().strip()
        if not source:
            messagebox.showerror("Choose a file", "Choose a video file first.")
            return
        path = Path(source)
        if not path.exists():
            messagebox.showerror("Missing file", "That file does not exist.")
            return
        out_dir = OUTPUTS_DIR / f"{int(time.time())}_{path.stem}_analysis"
        if self.memory_mode.get():
            out_dir = DEFAULT_VAULT
        self.run_command(self.base_command(str(path), out_dir), out_dir)

    def analyze_url(self) -> None:
        source = self.url.get().strip()
        if not source:
            messagebox.showerror("Paste a URL", "Paste a public URL first.")
            return
        if not source.startswith(("http://", "https://")):
            messagebox.showerror("Invalid URL", "The URL must start with http:// or https://.")
            return
        safe = "".join(ch if ch.isalnum() else "_" for ch in source[:60]).strip("_") or "url"
        out_dir = OUTPUTS_DIR / f"{int(time.time())}_{safe}_analysis"
        if self.memory_mode.get():
            out_dir = DEFAULT_VAULT
        self.run_command(self.base_command(source, out_dir), out_dir)

    def run_command(self, command: list[str], out_dir: Path) -> None:
        if self.running:
            messagebox.showinfo("Job running", "Wait for the current job to finish.")
            return
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        self.output_dir = out_dir
        self.running = True
        self.status.set("Running analysis...")
        self.log_text.delete("1.0", tk.END)
        self.log_text.insert(tk.END, "Command:\n" + " ".join(command) + "\n\n")
        thread = threading.Thread(target=self.worker, args=(command,), daemon=True)
        thread.start()

    def worker(self, command: list[str]) -> None:
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(ROOT),
            )
            assert process.stdout is not None
            for line in process.stdout:
                self.log_queue.put(line)
            code = process.wait()
            self.log_queue.put(f"\nExit code: {code}\n")
            self.log_queue.put("__DONE__" if code == 0 else "__FAILED__")
        except Exception as exc:  # noqa: BLE001
            self.log_queue.put(f"\nFailed to run analysis: {exc}\n__FAILED__")

    def drain_log_queue(self) -> None:
        while True:
            try:
                item = self.log_queue.get_nowait()
            except queue.Empty:
                break
            if item == "__DONE__":
                self.running = False
                self.status.set("Completed")
            elif item == "__FAILED__":
                self.running = False
                self.status.set("Failed")
            else:
                self.log_text.insert(tk.END, item)
                self.log_text.see(tk.END)
        self.after(200, self.drain_log_queue)

    def refresh_deps(self) -> None:
        self.deps_text.delete("1.0", tk.END)
        self.deps_text.insert(tk.END, "Checking...\n")

        def check() -> None:
            try:
                result = subprocess.run(
                    [sys.executable, str(INGEST_SCRIPT), "--check-deps"],
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=str(ROOT),
                )
                output = result.stdout
            except Exception as exc:  # noqa: BLE001
                output = f"Dependency check failed: {exc}"
            self.after(0, lambda: self.set_deps(output))

        threading.Thread(target=check, daemon=True).start()

    def set_deps(self, output: str) -> None:
        self.deps_text.delete("1.0", tk.END)
        self.deps_text.insert(tk.END, output)

    def open_output(self) -> None:
        if not self.output_dir:
            messagebox.showinfo("No output yet", "Run an analysis first.")
            return
        self.output_dir.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["explorer.exe", str(self.output_dir)])


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    app = VideoTool()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
