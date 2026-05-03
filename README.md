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
- optional assimilation sidecar

It is designed for learning from creator videos, coding walkthroughs, technical demos, and build logs without keeping bulky raw artifacts forever.

## Project Evolution

This repo has evolved in three clear stages.

### 1. Original: Artifact Extractor

The first version was a local video evidence tool. It took an authorized local
video, public unauthenticated video URL, or user-authorized screen recording and
produced analysis artifacts: metadata, audio, transcript, frames, OCR, contact
sheets, and `analysis_index.json`.

That was useful, but artifact-heavy. If you forgot `--output-dir`, raw frames,
audio, transcripts, OCR, contact sheets, and indexes could be written beside the
source video.

### 2. First Upgrade: Quarantine And Learning

The next version made the flow quarantine-first and learning-first:

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

### 3. Current: Structured Assimilation

The current version uses a structured lesson-compression pattern learned from
Trell's broader harness work. That outside harness process does not run this
repo, replace this repo, patch this repo, or become part of the video extraction
backend.

What this repo assimilates is the lesson structure:

`source -> problem -> lesson -> scope -> validation -> risk -> next use`

- `video_digest.py` now writes `06-ASSIMILATION-ASSETS/*-assimilation.json`
  in the learning vault. This captures source, evidence profile, decision queue,
  reusable lesson template, validation gate, risk, and next use so agents can
  upgrade a harness without blindly adopting video claims.

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

Digest mode writes three durable outputs:

- `01-DIGESTS/*`: full human-readable evidence note.
- `05-CODEX-IMPORTS/*`: compact agent import note.
- `06-ASSIMILATION-ASSETS/*`: machine-readable harness-upgrade sidecar.

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
