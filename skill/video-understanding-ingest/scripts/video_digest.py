#!/usr/bin/env python3
"""Create a markdown learning digest from a video source and clean raw artifacts by default."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


def default_vault() -> Path:
    configured = os.environ.get("VIDEO_LEARNING_VAULT")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / "Video-Learning-Vault"


def safe_slug(value: str, fallback: str = "video") -> str:
    value = Path(value).stem if not value.startswith(("http://", "https://")) else value
    value = re.sub(r"https?://", "", value)
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-._")
    return (value[:80] or fallback).lower()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
            if limit and len(rows) >= limit:
                break
    return rows


def extract_links(text: str) -> list[str]:
    links = sorted(set(re.findall(r"https?://[^\s)>\]}\"']+", text)))
    return links


def load_transcript(path: Path | None) -> tuple[str, list[dict[str, Any]]]:
    if not path or not path.exists():
        return "", []
    data = read_json(path)
    return data.get("text", ""), data.get("segments", [])


def format_tags(tags_arg: str | None) -> str:
    """Return a YAML list block for frontmatter tags."""
    if tags_arg:
        items = [t.strip() for t in tags_arg.replace(",", " ").split()]
    else:
        items = ["type/video-digest", "topic/tech", "topic/ai", "topic/code"]
    return "\n".join(f"  - {item}" for item in items)


def build_digest(
    source: str,
    analysis_dir: Path,
    vault: Path,
    title: str | None,
    creator: str | None,
    tags: str | None,
) -> tuple[Path, Path]:
    index = read_json(analysis_dir / "analysis_index.json")
    transcript_path = index.get("artifacts", {}).get("transcript")
    transcript_text, segments = load_transcript(Path(transcript_path) if transcript_path else None)
    ocr_path = index.get("artifacts", {}).get("ocr")
    ocr_rows = read_jsonl(Path(ocr_path), limit=200) if ocr_path else []
    ocr_text = "\n".join(row.get("text", "") for row in ocr_rows if row.get("text"))
    combined_text = "\n".join([transcript_text, ocr_text])
    links = extract_links(combined_text + "\n" + source)

    analyzed = dt.datetime.now().strftime("%Y-%m-%d")
    slug = safe_slug(title or creator or source)
    digest_dir = vault / "01-DIGESTS"
    import_dir = vault / "05-CODEX-IMPORTS"
    link_dir = vault / "03-REPOS-LINKS"
    digest_dir.mkdir(parents=True, exist_ok=True)
    import_dir.mkdir(parents=True, exist_ok=True)
    link_dir.mkdir(parents=True, exist_ok=True)

    note_title = title or slug.replace("-", " ").title()
    digest_path = digest_dir / f"{analyzed}-{slug}.md"
    import_path = import_dir / f"{analyzed}-{slug}-codex-import.md"

    segment_lines = []
    for seg in segments[:40]:
        start = seg.get("start")
        end = seg.get("end")
        text = seg.get("text", "").strip()
        if text:
            segment_lines.append(f"- `{start}`-`{end}`: {text}")

    ocr_lines = []
    for row in ocr_rows[:40]:
        text = row.get("text", "").strip()
        if text:
            ocr_lines.append(f"- `{row.get('timestamp_sec')}`: {text}")

    link_lines = [f"- {link}" for link in links] or ["- None detected automatically."]

    digest = f"""---
type: video-digest
source: "{source}"
creator: "{creator or ''}"
title: "{note_title}"
created: "{analyzed}"
tags:
{format_tags(tags)}
raw_artifacts: temporary
---

# {note_title}

## Codex Import Summary

This note was generated as a durable learning digest from a video source. Codex should use it to extract reusable build patterns, tools, repos, commands, and implementation ideas. A human/Codex follow-up pass should turn the evidence below into concise lessons.

## What Was Built Or Explained

- TODO: Summarize the system, workflow, build, or coding lesson demonstrated in the video.

## Key Ideas

- TODO: Extract the highest-signal ideas from transcript, OCR, and visual evidence.

## Step-By-Step Process

- TODO: Convert the video into an implementation sequence.

## Tools, Repos, Links

{chr(10).join(link_lines)}

## Code/System Patterns To Reuse

- TODO: Add patterns worth reusing in Codex/Claude Code sessions.

## Transcript Evidence Sample

{chr(10).join(segment_lines) if segment_lines else '- No transcript segments available.'}

## On-Screen Text Sample

{chr(10).join(ocr_lines) if ocr_lines else '- No OCR text available.'}

## Open Questions

- What parts need manual verification?
- Are any repos/tools mentioned visually but not captured by OCR?

## Temporary Artifact Policy

Raw extracted frames, audio, transcripts, and OCR files are temporary and should be deleted after digest generation unless audit evidence is explicitly required.
"""

    codex_import = f"""# Codex Import: {note_title}

Source: {source}
Creator: {creator or 'Unknown'}
Analyzed: {analyzed}

## Use This In Future Sessions

- TODO: Condense the video into durable instructions Codex should apply.
- TODO: Include repos, tools, commands, architecture patterns, and implementation caveats.

## Links

{chr(10).join(link_lines)}

## Evidence Note

Full digest: [[{digest_path.stem}]]
"""

    digest_path.write_text(digest, encoding="utf-8")
    import_path.write_text(codex_import, encoding="utf-8")

    if links:
        link_note = link_dir / f"{analyzed}-{slug}-links.md"
        link_note.write_text(f"# Links From {note_title}\n\n" + "\n".join(link_lines) + "\n", encoding="utf-8")

    return digest_path, import_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a durable Obsidian learning digest from a video source.")
    parser.add_argument("source", help="Local video path or public URL.")
    parser.add_argument("--vault", type=Path, default=default_vault())
    parser.add_argument("--title", default=None)
    parser.add_argument("--creator", default=None)
    parser.add_argument("--tags", default=None)
    parser.add_argument("--frame-mode", choices=["sample", "key", "all", "none"], default="sample")
    parser.add_argument("--fps", default="1")
    parser.add_argument("--transcribe", choices=["auto", "whisper", "openai", "none"], default="auto")
    parser.add_argument("--ocr", choices=["auto", "tesseract", "none"], default="auto")
    parser.add_argument("--url-mode", choices=["auto", "direct", "yt-dlp"], default="auto")
    parser.add_argument("--keep-artifacts", action="store_true", help="Keep temporary extraction folder for audit/debugging.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    script = Path(__file__).with_name("video_ingest.py")
    temp_root = Path(tempfile.mkdtemp(prefix="video-digest-"))
    analysis_dir = temp_root / "analysis"
    cmd = [
        sys.executable,
        str(script),
        args.source,
        "--output-dir",
        str(analysis_dir),
        "--url-mode",
        args.url_mode,
        "--frame-mode",
        args.frame_mode,
        "--fps",
        args.fps,
        "--transcribe",
        args.transcribe,
        "--ocr",
        args.ocr,
    ]

    try:
        subprocess.run(cmd, check=True)
        digest_path, import_path = build_digest(args.source, analysis_dir, args.vault, args.title, args.creator, args.tags)
        print(f"Digest: {digest_path}")
        print(f"Codex import: {import_path}")
        if args.keep_artifacts:
            print(f"Kept artifacts: {analysis_dir}")
        return 0
    finally:
        if not args.keep_artifacts:
            shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
