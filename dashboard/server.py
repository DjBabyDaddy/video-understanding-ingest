#!/usr/bin/env python3
"""Local dashboard for the video-understanding-ingest skill."""

from __future__ import annotations

import json
import mimetypes
import os
import re
import subprocess
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
DATA_DIR = ROOT / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
OUTPUT_DIR = DATA_DIR / "outputs"
SKILL_DIR = Path(os.environ.get("VIDEO_INGEST_SKILL_DIR", REPO_ROOT / "skill" / "video-understanding-ingest")).expanduser()
INGEST_SCRIPT = SKILL_DIR / "scripts" / "video_ingest.py"
SCREEN_SCRIPT = SKILL_DIR / "scripts" / "screen_record_ingest.py"
MAX_BODY_BYTES = int(os.environ.get("VIDEO_DASHBOARD_MAX_UPLOAD_MB", "500")) * 1024 * 1024

JOBS: dict[str, dict[str, Any]] = {}
JOBS_LOCK = threading.Lock()


def json_response(handler: BaseHTTPRequestHandler, data: Any, status: int = 200) -> None:
    payload = json.dumps(data, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


def text_response(handler: BaseHTTPRequestHandler, data: str, status: int = 200, content_type: str = "text/plain") -> None:
    payload = data.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", f"{content_type}; charset=utf-8")
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


def is_path_within(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def safe_name(value: str, fallback: str = "video") -> str:
    stem = Path(value).stem or fallback
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-")
    return stem[:80] or fallback


def new_job(kind: str, label: str, command: list[str], output_dir: Path) -> str:
    job_id = time.strftime("%Y%m%d-%H%M%S") + f"-{len(JOBS) + 1}"
    with JOBS_LOCK:
        JOBS[job_id] = {
            "id": job_id,
            "kind": kind,
            "label": label,
            "status": "queued",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "command": command,
            "output_dir": str(output_dir),
            "analysis_index": str(output_dir / "analysis_index.json"),
            "exit_code": None,
            "log": "",
        }
    thread = threading.Thread(target=run_job, args=(job_id,), daemon=True)
    thread.start()
    return job_id


def append_log(job_id: str, line: str) -> None:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job is not None:
            job["log"] += line


def run_job(job_id: str) -> None:
    with JOBS_LOCK:
        job = JOBS[job_id]
        job["status"] = "running"
        command = list(job["command"])

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
            append_log(job_id, line)
        exit_code = process.wait()
        with JOBS_LOCK:
            job = JOBS[job_id]
            job["exit_code"] = exit_code
            job["status"] = "completed" if exit_code == 0 else "failed"
    except Exception as exc:  # noqa: BLE001
        with JOBS_LOCK:
            job = JOBS[job_id]
            job["status"] = "failed"
            job["exit_code"] = -1
            job["log"] += f"\nDashboard failed to start job: {exc}\n"


def read_body(handler: BaseHTTPRequestHandler) -> bytes:
    length = int(handler.headers.get("Content-Length", "0"))
    if length > MAX_BODY_BYTES:
        raise ValueError(f"Request is too large. Limit is {MAX_BODY_BYTES // 1024 // 1024} MB.")
    return handler.rfile.read(length)


def parse_multipart(handler: BaseHTTPRequestHandler) -> tuple[dict[str, str], dict[str, tuple[str, bytes]]]:
    content_type = handler.headers.get("Content-Type", "")
    match = re.search(r"boundary=(.+)", content_type)
    if not match:
        raise ValueError("Missing multipart boundary")
    boundary = match.group(1).strip().strip('"').encode("utf-8")
    body = read_body(handler)
    fields: dict[str, str] = {}
    files: dict[str, tuple[str, bytes]] = {}
    for raw_part in body.split(b"--" + boundary):
        part = raw_part.strip(b"\r\n")
        if not part or part == b"--":
            continue
        if b"\r\n\r\n" not in part:
            continue
        raw_headers, content = part.split(b"\r\n\r\n", 1)
        headers = raw_headers.decode("utf-8", errors="replace")
        disposition = next((line for line in headers.split("\r\n") if line.lower().startswith("content-disposition:")), "")
        name_match = re.search(r'name="([^"]+)"', disposition)
        if not name_match:
            continue
        name = name_match.group(1)
        filename_match = re.search(r'filename="([^"]*)"', disposition)
        if filename_match:
            filename = Path(filename_match.group(1)).name
            files[name] = (filename, content.rstrip(b"\r\n"))
        else:
            fields[name] = content.decode("utf-8", errors="replace").strip()
    return fields, files


def options_from_fields(fields: dict[str, str]) -> dict[str, str]:
    return {
        "frame_mode": fields.get("frame_mode", "sample"),
        "fps": fields.get("fps", "1"),
        "transcribe": fields.get("transcribe", "auto"),
        "ocr": fields.get("ocr", "auto"),
        "url_mode": fields.get("url_mode", "auto"),
    }


def build_ingest_command(source: str, output_dir: Path, options: dict[str, str]) -> list[str]:
    return [
        sys.executable,
        str(INGEST_SCRIPT),
        source,
        "--output-dir",
        str(output_dir),
        "--url-mode",
        options["url_mode"],
        "--frame-mode",
        options["frame_mode"],
        "--fps",
        options["fps"],
        "--transcribe",
        options["transcribe"],
        "--ocr",
        options["ocr"],
    ]


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "VideoDashboard/1.0"

    def do_GET(self) -> None:  # noqa: N802
        if not self.is_local_client():
            text_response(self, "Forbidden", 403)
            return
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            self.serve_file(ROOT / "static" / "index.html")
            return
        if parsed.path.startswith("/static/"):
            self.serve_file(ROOT / parsed.path.lstrip("/"))
            return
        if parsed.path == "/api/deps":
            self.handle_deps()
            return
        if parsed.path == "/api/jobs":
            with JOBS_LOCK:
                jobs = list(JOBS.values())[::-1]
            json_response(self, jobs)
            return
        if parsed.path.startswith("/api/jobs/"):
            job_id = parsed.path.rsplit("/", 1)[-1]
            with JOBS_LOCK:
                job = JOBS.get(job_id)
            json_response(self, job or {"error": "not found"}, 200 if job else 404)
            return
        text_response(self, "Not found", 404)

    def do_POST(self) -> None:  # noqa: N802
        if not self.is_local_client():
            text_response(self, "Forbidden", 403)
            return
        parsed = urllib.parse.urlparse(self.path)
        try:
            if parsed.path == "/api/analyze-upload":
                self.handle_upload()
                return
            if parsed.path == "/api/analyze-url":
                self.handle_url()
                return
            if parsed.path == "/api/open-output":
                self.handle_open_output()
                return
        except Exception as exc:  # noqa: BLE001
            json_response(self, {"error": str(exc)}, 500)
            return
        text_response(self, "Not found", 404)

    def serve_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            text_response(self, "Not found", 404)
            return
        payload = path.read_bytes()
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def handle_deps(self) -> None:
        result = subprocess.run(
            [sys.executable, str(INGEST_SCRIPT), "--check-deps"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(ROOT),
        )
        json_response(self, {"exit_code": result.returncode, "output": result.stdout})

    def handle_upload(self) -> None:
        fields, files = parse_multipart(self)
        if "video" not in files:
            raise ValueError("Choose a video file first")
        filename, content = files["video"]
        if not filename:
            raise ValueError("Uploaded file is missing a filename")
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        upload_path = UPLOAD_DIR / f"{int(time.time())}_{safe_name(filename)}{Path(filename).suffix}"
        upload_path.write_bytes(content)
        out_dir = OUTPUT_DIR / f"{upload_path.stem}_analysis"
        command = build_ingest_command(str(upload_path), out_dir, options_from_fields(fields))
        job_id = new_job("upload", filename, command, out_dir)
        json_response(self, {"job_id": job_id})

    def handle_url(self) -> None:
        fields = urllib.parse.parse_qs(read_body(self).decode("utf-8"), keep_blank_values=True)
        simple = {key: values[-1] for key, values in fields.items()}
        url = simple.get("url", "").strip()
        if not url:
            raise ValueError("Paste a URL first")
        if not url.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out_dir = OUTPUT_DIR / f"{int(time.time())}_{safe_name(url)}_analysis"
        command = build_ingest_command(url, out_dir, options_from_fields(simple))
        job_id = new_job("url", url, command, out_dir)
        json_response(self, {"job_id": job_id})

    def handle_open_output(self) -> None:
        data = json.loads(read_body(self).decode("utf-8"))
        path = Path(data.get("path", ""))
        if not path.exists():
            raise ValueError("Output path does not exist yet")
        if not is_path_within(path, OUTPUT_DIR):
            with JOBS_LOCK:
                job_dirs = {Path(job["output_dir"]).resolve() for job in JOBS.values()}
            if path.resolve() not in job_dirs:
                raise ValueError("Output path is not managed by this dashboard")
        subprocess.Popen(["explorer.exe", str(path)])
        json_response(self, {"ok": True})

    def is_local_client(self) -> bool:
        return self.client_address[0] in {"127.0.0.1", "::1", "localhost"}

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> int:
    (ROOT / "static").mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    host = "127.0.0.1"
    port = int(os.environ.get("VIDEO_DASHBOARD_PORT", "8765"))
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    print(f"http://{host}:{port}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
