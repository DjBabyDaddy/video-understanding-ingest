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


ASSIMILATION_SCHEMA = "video-assimilation-v1"


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


def compact_text(value: Any, limit: int = 240) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def artifact_names(index: dict[str, Any]) -> list[str]:
    artifacts = index.get("artifacts", {})
    if not isinstance(artifacts, dict):
        return []
    return sorted(name for name, value in artifacts.items() if value)


def sample_segments(segments: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for seg in segments[:limit]:
        text = compact_text(seg.get("text"))
        if not text:
            continue
        samples.append({"start": seg.get("start"), "end": seg.get("end"), "text": text})
    return samples


def sample_ocr_rows(ocr_rows: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for row in ocr_rows[:limit]:
        text = compact_text(row.get("text"))
        if not text:
            continue
        samples.append({"timestamp_sec": row.get("timestamp_sec"), "text": text})
    return samples


def build_assimilation_asset(
    source: str,
    title: str,
    analyzed: str,
    index: dict[str, Any],
    links: list[str],
    transcript_text: str,
    segments: list[dict[str, Any]],
    ocr_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Create a structured lesson asset without invoking outside automation."""
    available = artifact_names(index)
    warnings = index.get("warnings", [])
    if not isinstance(warnings, list):
        warnings = [str(warnings)]

    decisions = [
        {
            "status": "test-next",
            "reason": "Any named tool, repo, CLI, MCP, workflow, or claim from the video needs primary-source verification before it becomes a harness rule.",
            "evidence": "links/transcript/OCR samples",
        },
        {
            "status": "monetize",
            "reason": "If the lesson improves content generation, package the proof as a repeatable service, content asset, or client workflow.",
            "evidence": "human/Codex follow-up pass",
        },
    ]
    if not links:
        decisions.append(
            {
                "status": "watch",
                "reason": "No external links were detected automatically; a visual/manual pass may be needed before tool adoption.",
                "evidence": "link extraction returned none",
            }
        )
    if not transcript_text and not ocr_rows:
        decisions.append(
            {
                "status": "watch",
                "reason": "The digest has weak semantic evidence because no transcript or OCR text was captured.",
                "evidence": "missing transcript/OCR",
            }
        )

    return {
        "type": "VideoAssimilationAsset",
        "schema_version": ASSIMILATION_SCHEMA,
        "source": source,
        "title": title,
        "created": analyzed,
        "evidence_profile": {
            "available_artifacts": available,
            "transcript_segments": len(segments),
            "ocr_rows_sampled": len(ocr_rows),
            "links_detected": len(links),
            "warnings": warnings,
            "raw_artifacts_policy": "temporary unless --keep-artifacts is used",
        },
        "evidence_samples": {
            "transcript": sample_segments(segments),
            "ocr": sample_ocr_rows(ocr_rows),
            "links": links[:40],
        },
        "decision_queue": decisions,
        "evolution_template": {
            "source": source,
            "problem": "What recurring harness/content/workflow problem does this video expose?",
            "lesson": "What compact reusable rule, method, helper route, or prompt pattern should be retained?",
            "scope": "Which projects, lanes, data classes, or content types should use this lesson?",
            "validation": "What primary source, local test, proof output, or human approval is required before adoption?",
            "risk": "What could go wrong: privacy, platform rules, tool trust, cost, client exposure, or hallucinated claims?",
            "next_use": "The next concrete task where this lesson should be applied.",
        },
        "promotion_gate": {
            "adopt_now_requires": [
                "primary-source verification for named tools/repos/claims",
                "local smoke test or small proof output when behavior changes",
                "harness doc/helper registry/shared memory update",
            ],
            "publish_requires": [
                "rights/data-class approval",
                "sanitized derivative or summary only",
                "no raw private media or credentials",
            ],
        },
    }


def format_assimilation_markdown(asset: dict[str, Any]) -> str:
    profile = asset["evidence_profile"]
    decisions = asset["decision_queue"]
    template = asset["evolution_template"]
    gates = asset["promotion_gate"]
    decision_lines = [
        f"- `{item['status']}`: {item['reason']} Evidence: {item['evidence']}"
        for item in decisions
    ]
    return f"""## Structured Assimilation Asset

This section applies a structured lesson-compression pattern to video learning: source signal -> problem -> reusable lesson -> scope -> validation -> risk -> next use. It is a decision aid, not an automatic code patch.

Evidence profile:

- Available artifacts: {", ".join(profile["available_artifacts"]) or "none"}
- Transcript segments: {profile["transcript_segments"]}
- OCR rows sampled: {profile["ocr_rows_sampled"]}
- Links detected: {profile["links_detected"]}
- Raw artifact policy: {profile["raw_artifacts_policy"]}

Decision queue:

{chr(10).join(decision_lines)}

Evolution template:

- Source: {template["source"]}
- Problem: {template["problem"]}
- Lesson: {template["lesson"]}
- Scope: {template["scope"]}
- Validation: {template["validation"]}
- Risk: {template["risk"]}
- Next use: {template["next_use"]}

Promotion gate:

- Adopt now requires: {"; ".join(gates["adopt_now_requires"])}
- Publish requires: {"; ".join(gates["publish_requires"])}
"""


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
    assimilation_dir = vault / "06-ASSIMILATION-ASSETS"
    digest_dir.mkdir(parents=True, exist_ok=True)
    import_dir.mkdir(parents=True, exist_ok=True)
    link_dir.mkdir(parents=True, exist_ok=True)
    assimilation_dir.mkdir(parents=True, exist_ok=True)

    note_title = title or slug.replace("-", " ").title()
    digest_path = digest_dir / f"{analyzed}-{slug}.md"
    import_path = import_dir / f"{analyzed}-{slug}-codex-import.md"
    assimilation_path = assimilation_dir / f"{analyzed}-{slug}-assimilation.json"

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
    assimilation_asset = build_assimilation_asset(source, note_title, analyzed, index, links, transcript_text, segments, ocr_rows)
    assimilation_asset["durable_outputs"] = {
        "digest": str(digest_path),
        "codex_import": str(import_path),
        "assimilation_asset": str(assimilation_path),
    }
    assimilation_markdown = format_assimilation_markdown(assimilation_asset)

    digest = f"""---
type: video-digest
source: "{source}"
creator: "{creator or ''}"
title: "{note_title}"
created: "{analyzed}"
tags:
{format_tags(tags)}
raw_artifacts: temporary
assimilation_schema: "{ASSIMILATION_SCHEMA}"
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

{assimilation_markdown}

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

## Assimilation Asset

JSON sidecar: `{assimilation_path}`

Use the sidecar to turn this video into verified harness updates. Do not promote a tool, repo, workflow, MCP, or public claim until the promotion gate is satisfied.

## Evidence Note

Full digest: [[{digest_path.stem}]]
"""

    digest_path.write_text(digest, encoding="utf-8")
    import_path.write_text(codex_import, encoding="utf-8")
    assimilation_path.write_text(json.dumps(assimilation_asset, indent=2), encoding="utf-8")

    if links:
        link_note = link_dir / f"{analyzed}-{slug}-links.md"
        link_note.write_text(f"# Links From {note_title}\n\n" + "\n".join(link_lines) + "\n", encoding="utf-8")

    return digest_path, import_path, assimilation_path


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
        digest_path, import_path, assimilation_path = build_digest(args.source, analysis_dir, args.vault, args.title, args.creator, args.tags)
        print(f"Digest: {digest_path}")
        print(f"Codex import: {import_path}")
        print(f"Assimilation asset: {assimilation_path}")
        if args.keep_artifacts:
            print(f"Kept artifacts: {analysis_dir}")
        return 0
    finally:
        if not args.keep_artifacts:
            shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
