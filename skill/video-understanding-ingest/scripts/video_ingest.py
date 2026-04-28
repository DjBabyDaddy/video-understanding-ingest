#!/usr/bin/env python3
"""Create analysis-ready artifacts from an authorized local video or public URL."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi", ".mpeg", ".mpg", ".wmv"}
TOOL_ENV_VARS = {
    "ffmpeg": "VIDEO_INGEST_FFMPEG",
    "ffprobe": "VIDEO_INGEST_FFPROBE",
    "yt-dlp": "VIDEO_INGEST_YTDLP",
    "whisper": "VIDEO_INGEST_WHISPER",
    "tesseract": "VIDEO_INGEST_TESSERACT",
}


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def require_tool(name: str) -> str:
    path = resolve_tool(name)
    if path:
        return path
    raise SystemExit(f"Required tool not found on PATH or known fallback locations: {name}")


def resolve_tool(name: str) -> str | None:
    env_var = TOOL_ENV_VARS.get(name)
    if env_var:
        configured = os.environ.get(env_var)
        if configured and Path(configured).expanduser().exists():
            return str(Path(configured).expanduser().resolve())
    path = shutil.which(name)
    if path:
        return path
    return None


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def is_http_url(source: str) -> bool:
    parsed = urllib.parse.urlparse(source)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def safe_stem(value: str, fallback: str = "video") -> str:
    parsed = urllib.parse.urlparse(value)
    base = Path(parsed.path).stem if parsed.scheme else Path(value).stem
    if not base:
        base = parsed.netloc or fallback
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._-")
    return base[:80] or fallback


def extension_from_response(url: str, content_type: str | None) -> str:
    suffix = Path(urllib.parse.urlparse(url).path).suffix.lower()
    if suffix in VIDEO_EXTENSIONS:
        return suffix
    if content_type:
        guessed = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if guessed in VIDEO_EXTENSIONS:
            return guessed
    return ".mp4"


def resolve_source(source: str, output_dir: Path, url_mode: str, warnings: list[str]) -> tuple[Path, dict[str, Any]]:
    if is_http_url(source):
        source_dir = output_dir / "source"
        source_dir.mkdir(parents=True, exist_ok=True)
        provenance = {"kind": "url", "url": source, "url_mode": url_mode}
        if url_mode == "direct":
            video = download_direct_url(source, source_dir)
        elif url_mode == "yt-dlp":
            video = download_with_ytdlp(source, source_dir)
            provenance["downloader"] = "yt-dlp"
        else:
            try:
                video = download_direct_url(source, source_dir)
                provenance["downloader"] = "urllib"
            except RuntimeError as exc:
                warnings.append(f"Direct URL download skipped: {exc}")
                video = download_with_ytdlp(source, source_dir)
                provenance["downloader"] = "yt-dlp"
        provenance["local_path"] = str(video)
        write_json(output_dir / "source" / "source_provenance.json", provenance)
        return video, provenance

    video = Path(source).expanduser().resolve()
    if not video.exists() or not video.is_file():
        raise SystemExit(f"Video file not found: {video}")
    return video, {"kind": "local_file", "local_path": str(video)}


def download_direct_url(url: str, source_dir: Path) -> Path:
    request = urllib.request.Request(url, headers={"User-Agent": "video-understanding-ingest/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        content_type = response.headers.get("Content-Type")
        suffix = Path(urllib.parse.urlparse(url).path).suffix.lower()
        is_videoish = (content_type or "").lower().startswith("video/") or suffix in VIDEO_EXTENSIONS
        if not is_videoish:
            raise RuntimeError(f"URL does not look like a direct video file. Content-Type={content_type!r}")
        out = source_dir / f"source{extension_from_response(url, content_type)}"
        with out.open("wb") as f:
            shutil.copyfileobj(response, f)
    return out.resolve()


def download_with_ytdlp(url: str, source_dir: Path) -> Path:
    ytdlp_cmd = ytdlp_command()
    before = {p.resolve() for p in source_dir.glob("source.*")}
    run(
        ytdlp_cmd
        + [
            "--no-playlist",
            "--restrict-filenames",
            "--merge-output-format",
            "mp4",
            "-P",
            str(source_dir),
            "-o",
            "source.%(ext)s",
            url,
        ]
    )
    candidates = [
        p.resolve()
        for p in source_dir.glob("source.*")
        if p.resolve() not in before and p.suffix.lower() not in {".part", ".ytdl", ".json"}
    ]
    if not candidates:
        candidates = [
            p.resolve()
            for p in source_dir.glob("source.*")
            if p.suffix.lower() not in {".part", ".ytdl", ".json"}
        ]
    if not candidates:
        raise RuntimeError("yt-dlp completed without producing a source video file.")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def ytdlp_command() -> list[str]:
    try:
        import yt_dlp  # noqa: F401

        return [sys.executable, "-m", "yt_dlp"]
    except Exception:
        return [require_tool("yt-dlp")]


def ffprobe_json(video: Path) -> dict[str, Any]:
    ffprobe = require_tool("ffprobe")
    result = run(
        [
            ffprobe,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(video),
        ]
    )
    return json.loads(result.stdout)


def ffprobe_frames(video: Path) -> list[dict[str, Any]]:
    ffprobe = require_tool("ffprobe")
    result = run(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "frame=best_effort_timestamp_time,pkt_pts_time,pict_type,coded_picture_number",
            "-print_format",
            "json",
            str(video),
        ]
    )
    frames = json.loads(result.stdout).get("frames", [])
    normalized: list[dict[str, Any]] = []
    for idx, frame in enumerate(frames):
        ts = frame.get("best_effort_timestamp_time") or frame.get("pkt_pts_time")
        try:
            timestamp = float(ts) if ts is not None else None
        except ValueError:
            timestamp = None
        normalized.append(
            {
                "source_frame_index": idx,
                "timestamp_sec": timestamp,
                "pict_type": frame.get("pict_type"),
            }
        )
    return normalized


def extract_audio(video: Path, audio_path: Path) -> None:
    ffmpeg = require_tool("ffmpeg")
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(video),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            str(audio_path),
        ]
    )


def extract_frames(video: Path, frames_dir: Path, mode: str, fps: float) -> list[Path]:
    ffmpeg = require_tool("ffmpeg")
    frames_dir.mkdir(parents=True, exist_ok=True)
    pattern = frames_dir / "frame_%06d.jpg"
    if mode == "none":
        return []
    if mode == "sample":
        vf = f"fps={fps}"
        cmd = [ffmpeg, "-y", "-i", str(video), "-vf", vf, "-q:v", "2", str(pattern)]
    elif mode == "key":
        cmd = [
            ffmpeg,
            "-y",
            "-i",
            str(video),
            "-vf",
            r"select=eq(pict_type\,I)",
            "-vsync",
            "vfr",
            "-q:v",
            "2",
            str(pattern),
        ]
    elif mode == "all":
        cmd = [ffmpeg, "-y", "-i", str(video), "-vsync", "0", "-q:v", "2", str(pattern)]
    else:
        raise ValueError(f"Unknown frame mode: {mode}")
    run(cmd)
    return sorted(frames_dir.glob("frame_*.jpg"))


def duration_from_metadata(metadata: dict[str, Any]) -> float | None:
    raw = metadata.get("format", {}).get("duration")
    try:
        return float(raw) if raw is not None else None
    except ValueError:
        return None


def build_frame_manifest(
    image_paths: list[Path],
    source_frames: list[dict[str, Any]],
    mode: str,
    fps: float,
    duration: float | None,
    output_path: Path,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if mode == "all":
        selected = source_frames
    elif mode == "key":
        selected = [f for f in source_frames if f.get("pict_type") == "I"]
    else:
        selected = []

    for i, image in enumerate(image_paths, start=1):
        source: dict[str, Any] = {}
        if mode in {"all", "key"} and i - 1 < len(selected):
            source = selected[i - 1]
        elif mode == "sample":
            timestamp = (i - 1) / fps
            if duration is not None:
                timestamp = min(timestamp, duration)
            nearest = nearest_frame(source_frames, timestamp)
            source = {
                "timestamp_sec": timestamp,
                "source_frame_index": nearest.get("source_frame_index") if nearest else None,
                "pict_type": nearest.get("pict_type") if nearest else None,
            }
        row = {
            "sequence": i,
            "timestamp_sec": source.get("timestamp_sec"),
            "source_frame_index": source.get("source_frame_index"),
            "pict_type": source.get("pict_type"),
            "path": str(image.resolve()),
        }
        rows.append(row)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return rows


def nearest_frame(frames: list[dict[str, Any]], timestamp: float) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    best_delta = math.inf
    for frame in frames:
        ts = frame.get("timestamp_sec")
        if ts is None:
            continue
        delta = abs(float(ts) - timestamp)
        if delta < best_delta:
            best = frame
            best_delta = delta
    return best


def transcribe(audio_path: Path, transcript_dir: Path, mode: str, language: str | None, warnings: list[str]) -> Path | None:
    if mode == "none":
        return None
    transcript_dir.mkdir(parents=True, exist_ok=True)
    whisper = resolve_tool("whisper")
    if mode in {"auto", "whisper"} and whisper:
        return transcribe_whisper(audio_path, transcript_dir, language, whisper)
    if mode == "whisper":
        warnings.append("Whisper CLI requested but not found on PATH.")
        return None
    if mode in {"auto", "openai"}:
        if os.environ.get("OPENAI_API_KEY"):
            try:
                return transcribe_openai(audio_path, transcript_dir, language)
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"OpenAI transcription failed: {exc}")
                return None
        if mode == "openai":
            warnings.append("OpenAI transcription requested but OPENAI_API_KEY is not set.")
    if mode == "auto":
        warnings.append("No transcription engine available. Install whisper CLI or set OPENAI_API_KEY with the openai Python package.")
    return None


def transcribe_whisper(audio_path: Path, transcript_dir: Path, language: str | None, whisper: str) -> Path:
    cmd = [
        whisper,
        str(audio_path),
        "--output_dir",
        str(transcript_dir),
        "--output_format",
        "json",
    ]
    if language:
        cmd.extend(["--language", language])
    run(cmd)
    raw_candidates = sorted(transcript_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not raw_candidates:
        raise RuntimeError("Whisper finished without producing JSON output.")
    raw_path = raw_candidates[0]
    raw = read_json(raw_path)
    normalized = {
        "engine": "whisper-cli",
        "language": raw.get("language"),
        "text": raw.get("text", ""),
        "segments": [
            {
                "start": seg.get("start"),
                "end": seg.get("end"),
                "text": seg.get("text", "").strip(),
            }
            for seg in raw.get("segments", [])
        ],
        "raw_path": str(raw_path.resolve()),
    }
    out = transcript_dir / "transcript.json"
    write_json(out, normalized)
    return out


def transcribe_openai(audio_path: Path, transcript_dir: Path, language: str | None) -> Path:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("The openai Python package is not installed.") from exc

    client = OpenAI()
    with audio_path.open("rb") as audio_file:
        kwargs: dict[str, Any] = {
            "model": "gpt-4o-transcribe",
            "file": audio_file,
        }
        if language:
            kwargs["language"] = language
        result = client.audio.transcriptions.create(**kwargs)
    text = getattr(result, "text", None) or str(result)
    normalized = {
        "engine": "openai",
        "language": language,
        "text": text,
        "segments": [],
        "raw_path": None,
    }
    out = transcript_dir / "transcript.json"
    write_json(out, normalized)
    return out


def run_ocr(manifest: list[dict[str, Any]], ocr_dir: Path, mode: str, warnings: list[str]) -> Path | None:
    if mode == "none" or not manifest:
        return None
    try:
        from PIL import Image
        import pytesseract
    except ImportError:
        if mode in {"auto", "tesseract"}:
            warnings.append("OCR skipped. Install pillow and pytesseract, and install the Tesseract binary.")
        return None

    tesseract = resolve_tool("tesseract")
    if mode == "tesseract" and not tesseract:
        warnings.append("Tesseract OCR binary requested but not found on PATH.")
        return None
    if tesseract:
        pytesseract.pytesseract.tesseract_cmd = tesseract

    ocr_dir.mkdir(parents=True, exist_ok=True)
    out = ocr_dir / "frame_ocr.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for row in manifest:
            path = row["path"]
            try:
                text = pytesseract.image_to_string(Image.open(path)).strip()
            except Exception as exc:  # noqa: BLE001
                text = ""
                warnings.append(f"OCR failed for {path}: {exc}")
            f.write(
                json.dumps(
                    {
                        "sequence": row["sequence"],
                        "timestamp_sec": row.get("timestamp_sec"),
                        "path": path,
                        "text": text,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    return out


def create_contact_sheets(manifest: list[dict[str, Any]], sheet_dir: Path, warnings: list[str], every: int = 1) -> list[Path]:
    if not manifest:
        return []
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        warnings.append("Contact sheets skipped. Install pillow to enable them.")
        return []

    selected = manifest[:: max(1, every)]
    sheet_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    thumb_w, thumb_h = 240, 135
    label_h = 24
    cols = 4
    rows_per_sheet = 5
    per_sheet = cols * rows_per_sheet
    for sheet_idx in range(0, len(selected), per_sheet):
        chunk = selected[sheet_idx : sheet_idx + per_sheet]
        sheet = Image.new("RGB", (cols * thumb_w, rows_per_sheet * (thumb_h + label_h)), "white")
        draw = ImageDraw.Draw(sheet)
        for idx, row in enumerate(chunk):
            x = (idx % cols) * thumb_w
            y = (idx // cols) * (thumb_h + label_h)
            try:
                img = Image.open(row["path"]).convert("RGB")
                img.thumbnail((thumb_w, thumb_h))
                sheet.paste(img, (x, y))
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"Contact sheet image failed for {row['path']}: {exc}")
            ts = row.get("timestamp_sec")
            label = f"{row['sequence']} @ {ts:.2f}s" if isinstance(ts, (int, float)) else str(row["sequence"])
            draw.text((x + 4, y + thumb_h + 4), label, fill="black")
        out = sheet_dir / f"contact_sheet_{len(paths) + 1:03d}.jpg"
        sheet.save(out, quality=90)
        paths.append(out)
    return paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create analysis-ready artifacts from a local video or public URL.")
    parser.add_argument("source", nargs="?", help="Local video file or public unauthenticated HTTP(S) URL to ingest.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Directory for generated artifacts.")
    parser.add_argument("--url-mode", choices=["auto", "direct", "yt-dlp"], default="auto", help="How to fetch HTTP(S) URLs.")
    parser.add_argument("--frame-mode", choices=["sample", "key", "all", "none"], default="sample")
    parser.add_argument("--fps", type=float, default=1.0, help="Frames per second when --frame-mode sample is used.")
    parser.add_argument("--transcribe", choices=["auto", "whisper", "openai", "none"], default="auto")
    parser.add_argument("--ocr", choices=["auto", "tesseract", "none"], default="auto")
    parser.add_argument("--language", default=None, help="Optional transcription/OCR language hint.")
    parser.add_argument("--contact-sheet-every", type=int, default=1, help="Use every Nth exported frame in contact sheets.")
    parser.add_argument("--check-deps", action="store_true", help="Print dependency availability and exit.")
    return parser.parse_args()


def check_deps() -> int:
    deps = {
        "ffmpeg": resolve_tool("ffmpeg"),
        "ffprobe": resolve_tool("ffprobe"),
        "yt-dlp": resolve_tool("yt-dlp"),
        "whisper": resolve_tool("whisper"),
        "tesseract": resolve_tool("tesseract"),
    }
    py_deps = {}
    for name in ["PIL", "pytesseract", "openai"]:
        try:
            __import__(name)
            py_deps[name] = "FOUND"
        except ImportError:
            py_deps[name] = "NOT_FOUND"
        except Exception as exc:  # noqa: BLE001
            py_deps[name] = f"BROKEN ({type(exc).__name__}: {exc})"

    print("Binary dependencies:")
    for name, path in deps.items():
        status = path or "NOT_FOUND"
        required = " required" if name in {"ffmpeg", "ffprobe"} else " optional"
        print(f"  {name}:{required}: {status}")
    print("Python dependencies:")
    for name, status in py_deps.items():
        print(f"  {name}: optional: {status}")
    return 0 if deps["ffmpeg"] and deps["ffprobe"] else 2


def main() -> int:
    args = parse_args()
    if args.check_deps:
        return check_deps()
    if args.source is None:
        raise SystemExit("Source file or public URL is required unless --check-deps is used.")
    if args.fps <= 0:
        raise SystemExit("--fps must be greater than 0.")

    output_dir = args.output_dir
    if output_dir is None:
        if is_http_url(args.source):
            output_dir = Path.cwd() / f"{safe_stem(args.source)}_analysis"
        else:
            local_source = Path(args.source).expanduser().resolve()
            output_dir = local_source.parent / f"{local_source.stem}_analysis"
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    warnings: list[str] = []
    video, source_info = resolve_source(args.source, output_dir, args.url_mode, warnings)
    metadata = ffprobe_json(video)
    metadata_path = output_dir / "metadata.json"
    write_json(metadata_path, metadata)

    source_frames = ffprobe_frames(video) if args.frame_mode in {"all", "key"} else []
    audio_path = output_dir / "audio" / "audio.wav"
    extract_audio(video, audio_path)
    transcript_path = transcribe(audio_path, output_dir / "transcript", args.transcribe, args.language, warnings)

    image_paths = extract_frames(video, output_dir / "frames", args.frame_mode, args.fps)
    manifest_path = output_dir / "frames" / "frame_manifest.jsonl"
    manifest = build_frame_manifest(
        image_paths,
        source_frames,
        args.frame_mode,
        args.fps,
        duration_from_metadata(metadata),
        manifest_path,
    )
    ocr_path = run_ocr(manifest, output_dir / "ocr", args.ocr, warnings)
    contact_sheets = create_contact_sheets(manifest, output_dir / "contact_sheets", warnings, args.contact_sheet_every)

    index = {
        "source": source_info,
        "created_at": dt.datetime.now(dt.UTC).isoformat(),
        "options": {
            "url_mode": args.url_mode,
            "frame_mode": args.frame_mode,
            "fps": args.fps,
            "transcribe": args.transcribe,
            "ocr": args.ocr,
            "language": args.language,
            "contact_sheet_every": args.contact_sheet_every,
        },
        "artifacts": {
            "metadata": str(metadata_path),
            "audio": str(audio_path),
            "transcript": str(transcript_path) if transcript_path else None,
            "frame_manifest": str(manifest_path),
            "frames_dir": str((output_dir / "frames").resolve()),
            "ocr": str(ocr_path) if ocr_path else None,
            "contact_sheets": [str(p.resolve()) for p in contact_sheets],
        },
        "counts": {
            "exported_frames": len(image_paths),
            "source_frames_indexed": len(source_frames),
            "contact_sheets": len(contact_sheets),
        },
        "warnings": warnings,
    }
    index_path = output_dir / "analysis_index.json"
    write_json(index_path, index)
    print(str(index_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
