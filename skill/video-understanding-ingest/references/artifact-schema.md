# Video Ingest Artifact Schema

## analysis_index.json

- `source`: object describing the local file or URL source. For URLs, includes original URL, downloader, and local downloaded path.
- `created_at`: UTC timestamp for the ingest run.
- `options`: normalized command-line options.
- `artifacts`: paths to generated metadata, audio, transcript, frames, OCR, and contact sheets.
- `warnings`: non-fatal issues such as missing OCR or transcription tools.

## source/source_provenance.json

For URL ingests, records:

```json
{
  "kind": "url",
  "url": "https://example.com/video",
  "url_mode": "auto",
  "downloader": "urllib",
  "local_path": "C:\\analysis\\source\\source.mp4"
}
```

This file is not a license or permission record. It is provenance for analysis reproducibility.

## Screen Recording Output

`screen_record_ingest.py` writes:

- `recording.mkv`: the captured visible screen/window/region.
- `analysis/analysis_index.json`: the normal `video_ingest.py` analysis index for the recording.
- `analysis/*`: the standard metadata, audio, transcript, frame, OCR, and contact-sheet artifacts.

## frames/frame_manifest.jsonl

Each line is one exported frame:

```json
{
  "sequence": 1,
  "timestamp_sec": 12.04,
  "source_frame_index": 361,
  "pict_type": "P",
  "path": "C:\\analysis\\frames\\frame_000001.jpg"
}
```

`timestamp_sec` is based on `ffprobe` source frame metadata when available. For sampled mode, it is the nearest timeline estimate for the exported sample.

## transcript/transcript.json

The script normalizes successful transcription into:

```json
{
  "engine": "whisper-cli",
  "language": "en",
  "text": "Full transcript text...",
  "segments": [
    {
      "start": 0.0,
      "end": 3.2,
      "text": "Segment text"
    }
  ],
  "raw_path": "C:\\analysis\\transcript\\whisper_raw.json"
}
```

OpenAI transcription responses may not include segment-level timestamps depending on the model/response format. In that case, use the full text and align manually against frames/audio when precision matters.

## ocr/frame_ocr.jsonl

Each line is one OCR attempt:

```json
{
  "sequence": 1,
  "timestamp_sec": 12.04,
  "path": "C:\\analysis\\frames\\frame_000001.jpg",
  "text": "Detected on-screen text"
}
```

OCR quality depends on frame resolution, motion blur, subtitles, and installed Tesseract language packs.
