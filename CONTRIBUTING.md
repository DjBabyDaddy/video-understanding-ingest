# Contributing

Contributions are welcome if they preserve the safety boundary and local-first design.

Before opening a pull request:

1. Run the dependency check.
2. Run Python compile checks.
3. Do not include private videos, frames, audio, transcripts, cookies, browser profiles, API keys, or vault notes.
4. Keep platform access limited to public unauthenticated URLs or user-provided local files.

Useful checks:

```powershell
python .\skill\video-understanding-ingest\scripts\video_ingest.py --check-deps
python -m py_compile .\skill\video-understanding-ingest\scripts\video_ingest.py .\skill\video-understanding-ingest\scripts\video_digest.py .\skill\video-understanding-ingest\scripts\screen_record_ingest.py .\dashboard\server.py .\desktop\video_tool.py
```
