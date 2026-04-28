---
description: Analyze a video, public URL, or screen-recorded source into the Video Learning Vault as durable Codex/Claude memory
argument-hint: <video-path-or-public-url> [--title "..."] [--creator "..."] [--tags "topic/mcp,topic/ai"] [--frame-mode sample|key|all|none] [--fps 1] [--transcribe auto|openai|whisper|none] [--ocr auto|tesseract|none] [--keep-artifacts]
---

# Video Learn

Create a memory-first Obsidian digest from a video source, then enrich it with an LLM pass.

The user invoked this command with:

```text
$ARGUMENTS
```

## Behavior

- Write durable markdown notes to `--vault`, `VIDEO_LEARNING_VAULT`, or `~/Video-Learning-Vault`.
- Delete raw extraction artifacts by default.
- Keep raw artifacts only when `--keep-artifacts` is included.
- Do not bypass DRM, login walls, private content, cookies, auth headers, or platform access controls.

## Step 1 — Extract

Run the extraction script:

```powershell
python "$HOME\.codex\skills\video-understanding-ingest\scripts\video_digest.py" $ARGUMENTS
```

If `python` fails on Windows, retry with:

```powershell
py -3.12 "$HOME\.codex\skills\video-understanding-ingest\scripts\video_digest.py" $ARGUMENTS
```

Parse the output for the line that starts with `Digest:` — that path is the generated digest file.

## Step 2 — Enrich (LLM Pass)

After the script succeeds, read the digest file. Look at **Transcript Evidence Sample** and **On-Screen Text Sample** at the bottom — they are the raw evidence. Use them to fill in all `TODO` sections with real content:

### What Was Built Or Explained
Write 2–3 sentences describing what the video actually shows or teaches. Be specific: name the tool, repo, CLI, model, or concept demonstrated.

### Key Ideas
Extract 3–7 bullet points of the highest-signal insights, facts, numbers, or claims from the video. For AI news: include model names, benchmarks, release details. For repos/MCPs: include what the tool does and why it matters.

### Step-By-Step Process
If the video shows a how-to or build: write numbered implementation steps. If it's news/announcement coverage with no steps: write "N/A — informational video."

### Code/System Patterns To Reuse
List specific commands, patterns, repos, or architectural decisions worth reusing. Format like:
- `command or pattern` — what it does, when to use it
- Link to repo if mentioned

### Title Cleanup
If the title is a URL slug (e.g., contains `instagram.com`, `youtube.com`, or random characters), replace it with a clean descriptive title derived from the content.

### Codex Import Update
Also update the `05-CODEX-IMPORTS/` companion file:
- Replace `TODO: Condense the video...` with 3–5 concise bullet points a future Claude/Codex session should apply
- Keep it under 150 words total

### Learned Skill Candidate Update
If the video teaches a reusable procedure, tool selection rule, repo usage pattern, MCP/CLI workflow, or implementation decision, create or update a note in `04-PATTERNS/<slug>-pattern.md` with:

```yaml
---
type: learned-skill-candidate
status: candidate
source_digest: "[[digest-note-name]]"
skill_trigger: "When to use this lesson"
created: YYYY-MM-DD
tags:
  - video-learning
  - type/resource
---
```

Keep the pattern short: trigger, use case, steps, evidence link, and verification caveats. Do not call it an executable skill unless it has been promoted into a real `SKILL.md` folder.

## Step 3 — Write Back

Write the enriched content back to the digest, codex-import, and any learned-skill candidate file. Preserve existing frontmatter exactly unless creating a new pattern note. Only replace the TODO sections in existing generated files.

## Step 4 — MOC Hook

After saving, check if `_DASHBOARD/MOC-Video-Learning.md` and `04-RESOURCES/Learned Skills From Video.md` exist at the vault root. If they do, no action needed — Dataview picks up digests, imports, and learned-skill candidates automatically. If either is missing, note it to the user.

## If Arguments Are Missing

Ask the user for the video path or public URL, plus optional title/creator. Do not run the command without a source.

## Output

Report to the user:
1. The digest path
2. The 3 most important key ideas extracted
3. Any repos/links captured
