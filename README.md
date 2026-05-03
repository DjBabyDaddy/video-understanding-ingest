# Video Understanding Ingest

Local-first video learning tools for Codex, Claude Code, and Obsidian.

This project turns an authorized local video, public unauthenticated video URL, or user-authorized screen recording into analysis-ready data:

- ffprobe metadata
- extracted audio
- transcript via Whisper CLI or OpenAI API
- sampled, key, or all frames
- optional OCR
- contact sheets
- JSON artifact index
- optional Obsidian learning digest

It is designed for learning from creator videos, coding walkthroughs, technical demos, and build logs without keeping bulky raw artifacts forever.

## Why This Upgrade Is Different

The first release was useful but artifact-heavy: if you forgot `--output-dir`,
raw frames, audio, transcripts, OCR, contact sheets, and indexes were written
beside the source video.

The upgraded flow is quarantine-first and learning-first:

- `video_digest.py` is the preferred path for learning. It creates durable
  Obsidian-ready notes and removes temporary raw artifacts by default.
- `video_ingest.py` still creates full audit/debug evidence, but omitted
  `--output-dir` now writes to `VIDEO_INGEST_QUARANTINE_ROOT` or
  `~/Video-Ingest-Quarantine`.
- Dependency checks now show the active quarantine root and the runtime can add
  known FFmpeg/FFprobe locations to subprocesses so Whisper and FFmpeg-based
  steps work more reliably on Windows.
- The skill guidance now treats each video as a reusable source item: transcript,
  OCR, frames, metadata, and contact sheets feed tools, workflows, risks, content
  ideas, and implementation leads instead of stopping at raw extraction.

## Safety Boundary

Use this only for content you are allowed to access and process.

Do not use it to bypass DRM, login walls, private content, cookies, browser profiles, private API credentials, auth headers, platform access controls, or scraping restrictions. If a site blocks public unauthenticated download, use a lawful local file, creator-provided export, platform-provided download, or authorized visible screen recording.

## Install

Requirements:

- Python 3.11+
- FFmpeg and FFprobe on `PATH`
- Optional: `yt-dlp` for public supported pages
- Optional: `openai-whisper` or OpenAI API transcription
- Optional: Tesseract, Pillow, and pytesseract for OCR

Windows quick setup:

```powershell
winget install Gyan.FFmpeg
python -m pip install -r requirements.txt
```

Optional local Whisper:

```powershell
python -m pip install -r requirements-whisper.txt
```

Install the Codex/Claude skill copy:

```powershell
.\scripts\install.ps1
```

## Check Runtime

```powershell
python .\skill\video-understanding-ingest\scripts\video_ingest.py --check-deps
```

If a binary is not on `PATH`, set an explicit path:

```powershell
$env:VIDEO_INGEST_FFMPEG = "C:\path\to\ffmpeg.exe"
$env:VIDEO_INGEST_FFPROBE = "C:\path\to\ffprobe.exe"
$env:VIDEO_INGEST_YTDLP = "C:\path\to\yt-dlp.exe"
$env:VIDEO_INGEST_TESSERACT = "C:\path\to\tesseract.exe"
```

## CLI Usage

Analyze a local file:

```powershell
python .\skill\video-understanding-ingest\scripts\video_ingest.py "C:\path\to\video.mp4" --frame-mode sample --fps 1 --transcribe auto --ocr auto
```

Use `--output-dir .\analysis` only when you deliberately want artifacts in a
specific audit/debug folder.

Analyze a public unauthenticated URL:

```powershell
python .\skill\video-understanding-ingest\scripts\video_ingest.py "https://example.com/video.mp4" --output-dir .\analysis --url-mode auto
```

Create an Obsidian learning digest and remove raw artifacts afterward:

```powershell
$env:VIDEO_LEARNING_VAULT = "$HOME\Video-Learning-Vault"
python .\skill\video-understanding-ingest\scripts\video_digest.py "C:\path\to\video.mp4" --title "Agent workflow demo" --creator "Creator Name"
```

Use `--keep-artifacts` only when you need debug evidence.

## Dashboard

Run the local web dashboard:

```powershell
python .\dashboard\server.py
```

Open the printed `http://127.0.0.1:8765` URL. The dashboard binds to localhost only. Upload size defaults to 500 MB and can be changed:

```powershell
$env:VIDEO_DASHBOARD_MAX_UPLOAD_MB = "1000"
```

Run the desktop Tkinter tool:

```powershell
python .\desktop\video_tool.py
```

## Obsidian Memory

Set a durable vault path:

```powershell
$env:VIDEO_LEARNING_VAULT = "C:\path\to\Video-Learning-Vault"
```

The digest workflow writes compact Markdown notes instead of preserving raw frames/audio by default.

## License

MIT. See `LICENSE`.
