# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

Batch audio transcription pipeline using the `mlx-community/nemotron-3.5-asr-streaming-0.6b` model via Apple MLX. Accepts any ffmpeg-readable audio file, splits it into chunks internally, and writes the combined transcript to disk. Benchmarked at ~2h of audio transcribed in under 10 minutes on Apple Silicon.

## Environment

Uses Python 3.12 in a `uv`-managed virtual environment at `.venv/`. Always activate before running:

```bash
source .venv/bin/activate
```

Install deps: `uv pip install -e .` / dev deps: `uv pip install --group dev`

Key packages: `mlx-audio` 0.4.4, `mlx` 0.31.2, `mlx-lm` 0.31.3, `fastapi`, `uvicorn`.

## Running

**CLI:**
```bash
uv run mlx-nemotron <audio_file> [--output transcript.txt] [--chunk-seconds 30] [--language uk]
```

**HTTP server:**
```bash
python src/mlx_nemotron/server.py [--host 0.0.0.0] [--port 8000]

curl -X POST http://localhost:8000/transcribe -F "file=@audio.m4a"
curl -X POST http://localhost:8000/transcribe/path -H "Content-Type: application/json" -d '{"path": "/abs/path/audio.m4a"}'
curl http://localhost:8000/jobs/<job_id>
```

**Tests:**
```bash
uv run pytest
```

## Architecture

```
src/mlx_nemotron/
├── core.py     — transcribe(), split_audio_cached(), load_model(), file_cache_key()
├── cli.py      — argparse entry point (registered as mlx-nemotron script)
└── server.py   — FastAPI server; executor created fresh per lifespan
tests/
├── conftest.py — shared fixtures: audio_file, chunks_dir, mock_model
├── test_core.py
├── test_cli.py
└── test_server.py
```

## Key implementation details

- **Model cache**: stored in `.venv/hf_cache/` via `HF_HOME` env var set at import time in `core.py`. `HF_HUB_DISABLE_PROGRESS_BARS=1` suppresses HF download noise.
- **Chunk cache**: WAV chunks cached in `$TMPDIR/mlx_nemotron_chunks/<key>/` keyed by `sha256(path + size + mtime + chunk_seconds)[:16]`. Re-runs skip ffmpeg but always re-transcribe from cached chunks.
- **Model**: `mlx-community/nemotron-3.5-asr-streaming-0.6b`. `att_context_size=[56, 0]` is the causal streaming window.
- **Server concurrency**: executor is `max_workers=1` — MLX holds the GPU exclusively.
- **Language**: `None` = auto-detect; pass BCP-47 code (e.g. `"uk"`, `"en-US"`) to pin.
