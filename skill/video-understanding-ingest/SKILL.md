---
name: video-understanding-ingest
description: "Convert authorized local video files, public unauthenticated video URLs, or user-authorized screen recordings into analysis-ready artifacts: ffprobe metadata, extracted audio, speech transcript, sampled/key/all frames, frame manifests, optional OCR, contact sheets, and a JSON analysis index. Use when Codex needs to analyze Instagram/Reels/TikTok/YouTube-style videos or any video source for words, visuals, timing, on-screen text, claims, concepts, or creator research. Do not use this skill to bypass platform security, DRM, login walls, access controls, private content, or scraping restrictions."
---

# Video Understanding Ingest

## Boundary

Process only sources the user can lawfully access: local video files, user exports, creator-provided downloads, public unauthenticated URLs, or screen recordings the user is allowed to make under the applicable platform terms and law. If the user asks to bypass Instagram or another platform's protections, refuse that part and ask for a local file, authorized export, public URL, or user-authorized screen recording that does not require DRM circumvention, cookies, special headers, private API access, or access-control evasion.

This skill is for understanding video content after access has been resolved, not for defeating access controls.

## What Changed In The Upgraded Flow

The old flow was artifact-first: it created raw analysis folders beside the
source video unless every run provided an explicit `--output-dir`.

The upgraded flow is learning-first and quarantine-first:

1. Prefer `scripts/video_digest.py` when the goal is durable understanding. It
   extracts evidence, writes compact notes, and deletes temporary raw artifacts
   by default.
2. Use `scripts/video_ingest.py` when audit/debug artifacts are needed. If
   `--output-dir` is omitted, raw frames, audio, transcripts, OCR, contact
   sheets, and indexes go to a quarantine root instead of cluttering the source
   folder.
3. Treat each video as a reusable source item: extract tools, methods, claims,
   workflows, risks, content ideas, and implementation leads from transcript,
   OCR, frames, metadata, and contact sheets.
4. Verify primary sources before adopting tools, publishing claims, or creating
   client-facing content.
5. Keep raw/generated extraction artifacts in quarantine or a configured
   video-learning vault. Do not place raw video/audio/frame/OCR dumps in a Git
   workspace unless the data class allows it and the user explicitly asks.

## Structured Assimilation Pattern

The broader harness uses a lesson-compression pattern that is useful here, but
that outside process is not the video ingest engine. Do not combine the systems
or let any outside evolution process patch this skill during normal video work.

What video ingest owns:

- lawful media access boundary
- ffmpeg/ffprobe extraction
- transcript, OCR, frames, metadata, contact sheets
- quarantine and temporary artifact cleanup
- durable video-learning digest notes

What this skill assimilates:

- turn each video into an auditable source signal
- describe the recurring problem the video exposes
- compress the lesson into a reusable rule, method, helper route, or prompt
  pattern
- record scope, validation, risk, and next use before adoption
- keep a machine-readable sidecar for later harness evolution

`video_digest.py` now writes a `06-ASSIMILATION-ASSETS/*-assimilation.json`
sidecar in the video-learning vault. Treat that JSON as the bridge from video
evidence to harness upgrades. It is intentionally separate from raw extraction
artifacts, and it does not promote a tool, MCP, CLI, workflow, or public claim
without primary-source verification and the promotion gate in the sidecar.

Default quarantine root:

`VIDEO_INGEST_QUARANTINE_ROOT`, or `~/Video-Ingest-Quarantine` when the
environment variable is not set.

Override with `--quarantine-root` or `VIDEO_INGEST_QUARANTINE_ROOT` when a
project-specific quarantine is safer.

## Memory-First Workflow

When the user's goal is for Codex or Claude Code to learn from a video, prefer `scripts/video_digest.py` over `scripts/video_ingest.py`.

```powershell
python "$HOME\.codex\skills\video-understanding-ingest\scripts\video_digest.py" `
  "C:\path\to\video.mp4" `
  --title "Creator builds an agent workflow" `
  --creator "Creator Name" `
  --frame-mode sample `
  --fps 1 `
  --transcribe auto `
  --ocr auto
```

This writes durable markdown notes to:

the path passed with `--vault`, the `VIDEO_LEARNING_VAULT` environment variable, or `~/Video-Learning-Vault` by default.

and deletes raw extraction artifacts by default. Use `--keep-artifacts` only when audit/debug evidence is needed.

Read `references/vault-memory.md` before turning videos into durable knowledge.

## Quick Start

Requires `ffmpeg` and `ffprobe` on `PATH`. URL page extraction also requires `yt-dlp`; direct video URLs can be downloaded with Python's standard library. Optional enrichments require `whisper` for local transcription, or `OPENAI_API_KEY` plus the `openai` Python package for API transcription, and Tesseract plus `pillow`/`pytesseract` for OCR.

Check the current machine first:

```powershell
python "$HOME\.codex\skills\video-understanding-ingest\scripts\video_ingest.py" --check-deps
```

Use the bundled script for repeatable ingestion:

```powershell
python "$HOME\.codex\skills\video-understanding-ingest\scripts\video_ingest.py" `
  "C:\path\to\video.mp4" `
  --frame-mode sample `
  --fps 1 `
  --transcribe auto `
  --ocr auto
```

When `--output-dir` is omitted, generated artifacts go to the quarantine root.
Use `--output-dir` only for a deliberate audit/debug location.

For a public unauthenticated URL:

```powershell
python "$HOME\.codex\skills\video-understanding-ingest\scripts\video_ingest.py" `
  "https://example.com/path/to/video-or-public-page" `
  --output-dir "C:\path\to\analysis" `
  --url-mode auto `
  --frame-mode sample `
  --fps 1 `
  --transcribe auto `
  --ocr auto
```

Use `--url-mode direct` for direct `.mp4`, `.webm`, or similar media URLs. Use `--url-mode yt-dlp` for public pages supported by `yt-dlp`. Do not pass cookies, browser profiles, auth headers, or private URLs.

For a user-authorized visible screen recording:

```powershell
python "$HOME\.codex\skills\video-understanding-ingest\scripts\screen_record_ingest.py" `
  --duration 120 `
  --audio-device none `
  --frame-mode sample `
  --fps 1 `
  --transcribe auto `
  --ocr auto
```

List possible Windows audio capture devices first:

```powershell
python "$HOME\.codex\skills\video-understanding-ingest\scripts\screen_record_ingest.py" --list-audio-devices
```

For browser playback, use `--open-url` to open a visible Edge/Chrome window before recording. Prefer direct URL ingestion when possible. Headless/background browser capture is not reliable for audio+pixels; read `references/screen-recording.md` before promising it.

For exhaustive visual evidence, use `--frame-mode all`. Warn the user that this can create thousands of images and large JSONL files. For fast creator-research triage, use `--frame-mode sample --fps 1` or `--frame-mode key`.

## Workflow

1. Confirm the input is a local path, authorized artifact, public unauthenticated URL, or user-authorized screen recording.
2. Run `scripts/video_ingest.py` for files/URLs, or `scripts/screen_record_ingest.py` when the video can only be captured from visible playback.
3. Inspect `analysis_index.json` first; it points to every generated artifact.
4. Use transcript segments for spoken content, `frame_manifest.jsonl` for visual timing, and `frame_ocr.jsonl` for on-screen text.
5. For deeper visual reasoning, review the generated contact sheet and selected frames, then summarize scenes, claims, objects, charts, captions, and visual changes.

## Output Contract

The script writes a folder containing:

- `analysis_index.json`: top-level machine-readable map of inputs, options, artifacts, and warnings.
- `source/source_provenance.json`: original URL/local-source provenance when a URL is used.
- `metadata.json`: `ffprobe` format and stream metadata.
- `audio/audio.wav`: extracted mono 16 kHz audio for transcription or reuse.
- `transcript/transcript.json`: transcript data when OpenAI or Whisper transcription succeeds.
- `frames/frame_manifest.jsonl`: one JSON object per exported frame with sequence number, timestamp estimate, source frame metadata when available, and file path.
- `frames/*.jpg`: extracted frame images.
- `ocr/frame_ocr.jsonl`: optional OCR text per frame when Tesseract and Python bindings are installed.
- `contact_sheets/*.jpg`: optional visual overview sheets when Pillow is installed.

Read `references/artifact-schema.md` when you need the exact field meanings or need to build downstream analysis tooling.
Read `references/setup.md` when dependencies are missing.
Read `references/screen-recording.md` before screen-recording visible playback or discussing browser capture.
Read `references/vault-memory.md` before writing durable memory notes for Codex/Claude.

## Choosing Frame Mode

- `sample`: best default. Extracts frames at `--fps`, keeping output manageable while covering the full timeline.
- `key`: extracts likely scene-change/key frames. Good for quick narrative or setting analysis.
- `all`: exports every decodable video frame. Use only when the user explicitly needs exhaustive frame-level review and has enough disk/time.
- `none`: transcript/audio/metadata only.

## Transcription

Use `--transcribe auto` by default. The script tries local `whisper` CLI first, then the OpenAI Python SDK when `OPENAI_API_KEY` is set. Use `--transcribe none` if the user only wants visual artifacts.

Do not claim perfect transcription. Say that the output is a high-coverage transcript and that noisy audio, music, overlapping speech, accents, or platform compression may require manual spot checks.

## Analysis Guidance

When producing a final analysis from the artifacts, preserve evidence:

- Cite transcript segment timestamps when discussing spoken claims.
- Cite frame timestamps and image paths when discussing visual evidence.
- Merge speech, OCR, and frame changes into a timeline before summarizing.
- Keep uncertainty explicit when a frame is blurry, text is partially visible, or OCR/transcription confidence is unavailable.

For "nothing missed" requests, explain the practical limit: the script can export every frame and run full-audio transcription, but no automated process can guarantee perfect semantic understanding without review. Offer an exhaustive mode plus targeted manual validation of low-confidence areas.
