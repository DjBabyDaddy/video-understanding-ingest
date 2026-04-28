# Screen Recording Workflow

Use screen recording only for videos the user is allowed to view and record. Do not use it for DRM-protected streams, private content, login-gated content, or to bypass platform restrictions.

## Audio Reality on Windows

FFmpeg can capture the screen with `gdigrab`, but system audio capture depends on an available DirectShow input device. Common options:

- `Stereo Mix` if enabled by the audio driver.
- A loopback/virtual cable device installed by the user.
- A physical microphone, which is lower quality and includes room noise.

List available devices:

```powershell
python "$HOME\.codex\skills\video-understanding-ingest\scripts\screen_record_ingest.py" --list-audio-devices
```

Use the exact audio device name:

```powershell
python "$HOME\.codex\skills\video-understanding-ingest\scripts\screen_record_ingest.py" `
  --duration 120 `
  --audio-device "Stereo Mix (Realtek(R) Audio)" `
  --frame-mode sample `
  --fps 1
```

If no loopback device exists, use `--audio-device none` and rely on OCR/frames, or install/enable an audio loopback device outside this skill.

## Capture Scope

Full desktop:

```powershell
python "$HOME\.codex\skills\video-understanding-ingest\scripts\screen_record_ingest.py" --duration 60 --audio-device none
```

Region:

```powershell
python "$HOME\.codex\skills\video-understanding-ingest\scripts\screen_record_ingest.py" `
  --duration 60 `
  --region 100,100,1080,1920 `
  --audio-device none
```

Visible window title:

```powershell
python "$HOME\.codex\skills\video-understanding-ingest\scripts\screen_record_ingest.py" `
  --duration 60 `
  --window-title "Instagram - Google Chrome" `
  --audio-device none
```

Window capture requires the window to be visible and not minimized.

## Browser Use

For public direct/video-page URLs, prefer `video_ingest.py` with URL mode. It preserves the original media when possible and avoids screen-capture quality loss.

For a page that must be watched in a browser, `screen_record_ingest.py` can open a visible Edge/Chrome window before recording:

```powershell
python "$HOME\.codex\skills\video-understanding-ingest\scripts\screen_record_ingest.py" `
  --open-url "https://example.com/public-video-page" `
  --browser edge `
  --duration 120 `
  --warmup 5 `
  --audio-device "Stereo Mix (Realtek(R) Audio)"
```

Headless/background browser recording is not reliable for this use case: headless browsers usually do not expose normal screen pixels or system audio in the same way as a visible desktop session. If a true background flow is required, use direct URL ingestion or a platform API/export instead of screen recording.
