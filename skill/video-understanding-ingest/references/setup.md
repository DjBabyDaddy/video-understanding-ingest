# Video Ingest Setup

## Required

Install `ffmpeg`, which normally includes both `ffmpeg` and `ffprobe`.

Windows options:

```powershell
winget install Gyan.FFmpeg
```

or install from the official FFmpeg site and add the `bin` directory to `PATH`.

Verify:

```powershell
ffmpeg -version
ffprobe -version
```

## Optional Transcription

For local transcription:

```powershell
pip install -U openai-whisper
```

This installs the `whisper` CLI. It may also require PyTorch and can be slow on CPU.

For OpenAI API transcription:

```powershell
pip install -U openai
$env:OPENAI_API_KEY = "..."
```

## Optional OCR

Install the Tesseract binary and Python bindings:

```powershell
winget install UB-Mannheim.TesseractOCR
pip install -U pillow pytesseract
```

Verify:

```powershell
tesseract --version
python -c "import PIL, pytesseract; print('ocr ok')"
```

## Dependency Check

Run:

```powershell
python "$HOME\.codex\skills\video-understanding-ingest\scripts\video_ingest.py" --check-deps
```

`ffmpeg` and `ffprobe` are required. Missing transcription or OCR dependencies only disable those enrichments.

## Screen Recording

Screen recording uses FFmpeg's Windows `gdigrab` input for pixels and DirectShow (`dshow`) for optional audio devices.

Check audio devices:

```powershell
python "$HOME\.codex\skills\video-understanding-ingest\scripts\screen_record_ingest.py" --list-audio-devices
```

If no system-audio/loopback device appears, enable `Stereo Mix` in Windows sound settings or install a virtual audio cable. Without that, use `--audio-device none`.

## Optional Public URL Support

Direct media URLs work without extra Python packages. Public webpage URLs require `yt-dlp`:

```powershell
pip install -U yt-dlp
```

Verify:

```powershell
yt-dlp --version
```

Use only public unauthenticated URLs. Do not use cookies, browser sessions, private API credentials, or other access-control workarounds with this skill.
