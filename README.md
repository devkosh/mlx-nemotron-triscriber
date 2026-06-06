# mlx-nemotron-transcriber

Batch audio transcription using [`mlx-community/nemotron-3.5-asr-streaming-0.6b`](https://huggingface.co/mlx-community/nemotron-3.5-asr-streaming-0.6b) on Apple MLX.

**~2h of audio transcribed in under 10 minutes on Apple Silicon.**

---

## Requirements

- Apple Silicon Mac (M1/M2/M3/M4)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) — Python package manager
- [ffmpeg](https://ffmpeg.org/) — for audio splitting

```bash
brew install uv ffmpeg
```

---

## Setup

### 1. Create the virtual environment and install dependencies

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e .
```

For running tests, also install dev dependencies:

```bash
uv pip install --group dev
```

### 2. Download the model into the project

The model is stored inside `.venv/hf_cache/` to keep everything self-contained.

**Option A — download fresh (first time):**

```bash
HF_HOME=.venv/hf_cache .venv/bin/hf download mlx-community/nemotron-3.5-asr-streaming-0.6b
```

**Option B — move from your existing Hugging Face cache:**

```bash
mkdir -p .venv/hf_cache/hub
mv ~/.cache/huggingface/hub/models--mlx-community--nemotron-3.5-asr-streaming-0.6b \
   .venv/hf_cache/hub/
```

Verify:

```bash
ls .venv/hf_cache/hub/models--mlx-community--nemotron-3.5-asr-streaming-0.6b/snapshots/
# should show a commit hash directory
```

---

## Usage

### CLI

```bash
uv run mlx-nemotron <audio_file> [--output transcript.txt] [--chunk-seconds 30] [--language uk]
```

- `--output` defaults to `<stem>_transcript.txt` beside the input file
- `--language` defaults to auto-detect; pass a BCP-47 code (e.g. `uk`, `en-US`) to pin
- `--chunk-seconds` controls split size (30s is a good default)

**Examples:**

```bash
uv run mlx-nemotron interview.m4a
uv run mlx-nemotron lecture.mp3 --output lecture.txt --language en-US
```

WAV chunks are cached in `$TMPDIR/mlx_nemotron_chunks/` keyed by file path + mtime. Re-running the same file skips the ffmpeg split step.

### HTTP server

```bash
uv run mlx-nemotron serve [--host 0.0.0.0] [--port 8000]
```

The model loads once at startup. Jobs run one at a time (single GPU).

**Transcribe by file upload:**

```bash
curl -X POST http://localhost:8000/transcribe -F "file=@audio.m4a"
# → {"job_id": "...", "status": "pending"}
```

**Transcribe by path on disk:**

```bash
curl -X POST http://localhost:8000/transcribe/path \
  -H "Content-Type: application/json" \
  -d '{"path": "/abs/path/to/audio.m4a", "language": "uk"}'
```

**Poll for result:**

```bash
curl http://localhost:8000/jobs/<job_id>
# → {"status": "done", "transcript": "..."}
```

---

## Tests

```bash
uv run pytest
```

33 tests covering core transcription logic, CLI argument handling, and all server endpoints.
