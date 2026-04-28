# Video Learning Vault Memory Workflow

Default durable memory target:

- The `--vault` argument when supplied.
- Otherwise the `VIDEO_LEARNING_VAULT` environment variable when set.
- Otherwise `~/Video-Learning-Vault`.

Use this workflow when the user's goal is for Codex or Claude Code to learn from a video without storing bulky raw artifacts.

## Principle

Codex and Claude Code do not permanently train themselves from videos. They can reuse video knowledge when it is written into durable notes, skills, project docs, or task context. Therefore, transform video evidence into compact markdown notes that are easy to retrieve and read later.

## Default Outputs

- `01-DIGESTS/<date>-<slug>.md`: full durable video digest.
- `03-REPOS-LINKS/*.md`: optional extracted repo/link notes.
- `04-PATTERNS/*.md`: optional reusable system/pattern notes.
- `05-CODEX-IMPORTS/*.md`: short import-ready summary for future Codex/Claude sessions.

## Raw Artifact Policy

Use temporary folders for frames, transcripts, audio, and OCR. Delete them after writing the digest unless the user explicitly requests an audit trail.

## Digest Standards

Every digest should include:

- Source, creator, title, and date analyzed.
- What was built or explained.
- Key ideas and claims.
- Step-by-step implementation process.
- Tools, repos, packages, docs, links, and commands mentioned.
- Reusable patterns Codex should apply in future work.
- Open questions and uncertainty.
- Evidence pointers by timestamp when available.

Prefer concise, high-signal notes over dumping raw transcripts.
