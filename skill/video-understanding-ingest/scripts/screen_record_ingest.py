#!/usr/bin/env python3
"""Record an authorized on-screen video, then ingest the recording."""

from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

from video_ingest import require_tool


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def list_audio_devices() -> int:
    ffmpeg = require_tool("ffmpeg")
    result = run([ffmpeg, "-list_devices", "true", "-f", "dshow", "-i", "dummy"], check=False)
    output = "\n".join(part for part in [result.stdout, result.stderr] if part)
    print(output)
    return 0


def parse_region(region: str | None) -> tuple[int, int, int, int] | None:
    if not region:
        return None
    parts = [p.strip() for p in region.split(",")]
    if len(parts) != 4:
        raise SystemExit("--region must use x,y,width,height")
    try:
        x, y, width, height = [int(p) for p in parts]
    except ValueError as exc:
        raise SystemExit("--region values must be integers") from exc
    if width <= 0 or height <= 0:
        raise SystemExit("--region width and height must be greater than 0")
    return x, y, width, height


def launch_browser(url: str, browser: str, profile_dir: Path | None) -> subprocess.Popen[bytes] | None:
    browser_paths = {
        "edge": [
            Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
            Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        ],
        "chrome": [
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        ],
    }
    candidates = browser_paths.get(browser, [])
    exe = next((p for p in candidates if p.exists()), None)
    if not exe:
        print(f"Browser executable not found for {browser}; open the URL manually before recording.", file=sys.stderr)
        return None

    args = [
        str(exe),
        "--new-window",
        "--autoplay-policy=no-user-gesture-required",
        "--disable-features=PreloadMediaEngagementData,MediaEngagementBypassAutoplayPolicies",
    ]
    if profile_dir:
        profile_dir.mkdir(parents=True, exist_ok=True)
        args.append(f"--user-data-dir={profile_dir}")
    args.append(url)
    return subprocess.Popen(args)


def record_screen(args: argparse.Namespace, output_dir: Path) -> Path:
    ffmpeg = require_tool("ffmpeg")
    recording = output_dir / "recording.mkv"
    region = parse_region(args.region)

    cmd = [ffmpeg, "-y"]
    if args.duration:
        cmd.extend(["-t", str(args.duration)])

    cmd.extend(["-f", "gdigrab", "-framerate", str(args.framerate)])
    if region:
        x, y, width, height = region
        cmd.extend(["-offset_x", str(x), "-offset_y", str(y), "-video_size", f"{width}x{height}"])
    gdigrab_target = "desktop"
    if args.window_title:
        gdigrab_target = f"title={args.window_title}"
    cmd.extend(["-i", gdigrab_target])

    has_audio = bool(args.audio_device and args.audio_device.lower() != "none")
    if has_audio:
        cmd.extend(["-f", "dshow", "-i", f"audio={args.audio_device}"])

    cmd.extend(["-c:v", "libx264", "-preset", args.preset, "-pix_fmt", "yuv420p"])
    if has_audio:
        cmd.extend(["-c:a", "aac", "-b:a", "160k"])
    cmd.append(str(recording))

    print("Recording command:")
    print(" ".join(f'"{part}"' if " " in part else part for part in cmd))
    run(cmd)
    return recording


def ingest_recording(recording: Path, args: argparse.Namespace, output_dir: Path) -> None:
    ingest_dir = output_dir / "analysis"
    script = Path(__file__).with_name("video_ingest.py")
    cmd = [
        sys.executable,
        str(script),
        str(recording),
        "--output-dir",
        str(ingest_dir),
        "--frame-mode",
        args.frame_mode,
        "--fps",
        str(args.fps),
        "--transcribe",
        args.transcribe,
        "--ocr",
        args.ocr,
    ]
    if args.language:
        cmd.extend(["--language", args.language])
    result = run(cmd)
    if result.stdout.strip():
        print(result.stdout.strip())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record an authorized on-screen video and ingest it for analysis.")
    parser.add_argument("--list-audio-devices", action="store_true", help="List FFmpeg DirectShow audio devices and exit.")
    parser.add_argument("--duration", type=float, default=60.0, help="Recording duration in seconds.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Directory for recording and analysis artifacts.")
    parser.add_argument("--region", default=None, help="Optional capture region as x,y,width,height.")
    parser.add_argument("--window-title", default=None, help="Optional visible window title to capture instead of full desktop.")
    parser.add_argument("--framerate", type=int, default=30)
    parser.add_argument("--audio-device", default="none", help='DirectShow audio device name, or "none".')
    parser.add_argument("--preset", default="veryfast", help="FFmpeg x264 preset.")
    parser.add_argument("--open-url", default=None, help="Optional URL to open in a visible browser before recording.")
    parser.add_argument("--browser", choices=["edge", "chrome"], default="edge")
    parser.add_argument("--browser-profile-dir", type=Path, default=None, help="Optional temporary browser profile directory.")
    parser.add_argument("--warmup", type=float, default=5.0, help="Seconds to wait after opening a browser URL before recording.")
    parser.add_argument("--frame-mode", choices=["sample", "key", "all", "none"], default="sample")
    parser.add_argument("--fps", type=float, default=1.0)
    parser.add_argument("--transcribe", choices=["auto", "whisper", "openai", "none"], default="auto")
    parser.add_argument("--ocr", choices=["auto", "tesseract", "none"], default="auto")
    parser.add_argument("--language", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.list_audio_devices:
        return list_audio_devices()
    if args.duration <= 0:
        raise SystemExit("--duration must be greater than 0")

    output_dir = args.output_dir
    if output_dir is None:
        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path.cwd() / f"screen_recording_{stamp}"
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    browser_process = None
    if args.open_url:
        parsed = urllib.parse.urlparse(args.open_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise SystemExit("--open-url must be an http(s) URL")
        browser_process = launch_browser(args.open_url, args.browser, args.browser_profile_dir)
        if args.warmup > 0:
            time.sleep(args.warmup)

    recording = record_screen(args, output_dir)
    ingest_recording(recording, args, output_dir)

    if browser_process and args.browser_profile_dir:
        browser_process.terminate()
    print(str((output_dir / "analysis" / "analysis_index.json").resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
