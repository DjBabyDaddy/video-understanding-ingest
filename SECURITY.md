# Security Policy

## Supported Use

This project is for local-first analysis of videos the user is authorized to access and process.

Do not use it to defeat access controls, DRM, login walls, private APIs, cookies, auth headers, or platform protections.

## Data Handling

- Raw frames, audio, OCR, and transcripts may contain private information.
- `video_digest.py` deletes temporary raw artifacts by default unless `--keep-artifacts` is supplied.
- The dashboard stores uploads and outputs under `dashboard/data/`, which is ignored by git.
- Never commit `.env`, API keys, downloaded videos, extracted frames, transcripts, or private vault notes.

## Reporting Issues

Open a GitHub issue for non-sensitive bugs. For security-sensitive reports, avoid posting secrets, private videos, or exploit details publicly. Share the minimal reproduction and affected component.

## Local Dashboard Notes

The dashboard binds to `127.0.0.1` and rejects non-local clients. It enforces a request size limit through `VIDEO_DASHBOARD_MAX_UPLOAD_MB`. Treat it as a local convenience tool, not an internet-facing service.
