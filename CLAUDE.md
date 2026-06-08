# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

Batch audio transcription pipeline using the `mlx-community/nemotron-3.5-asr-streaming-0.6b` model via Apple MLX. Accepts any ffmpeg-readable audio file, splits it into 30s chunks internally, and writes the combined transcript to disk. Benchmarked at ~2h of audio transcribed in under 10 minutes on Apple Silicon.

The repo now ships in two parts:

1. **Python backend** (`src/mlx_nemotron/`) — the MLX-based transcription engine, exposed as a CLI and a FastAPI HTTP server.
2. **macOS SwiftUI app** (`macos_app/`) — a native companion that drives the backend, manages a local library of recordings + transcripts, and presents a drag-and-drop UI.

## Environment

Uses Python 3.12 in a `uv`-managed virtual environment at `.venv/`. Always activate before running:

```bash
source .venv/bin/activate
```

Install deps: `uv pip install -e .` / dev deps: `uv pip install --group dev`

Key Python packages: `mlx-audio` 0.4.4, `mlx` 0.31.2, `mlx-lm` 0.31.3, `fastapi`, `uvicorn`.

macOS app requires Xcode 15+ targeting macOS 14. Swift package dependency: `GRDB.swift` 6.x (SQLite wrapper).

## Running

**CLI (single file):**
```bash
uv run mlx-nemotron <audio_file> [--output transcript.txt] [--chunk-seconds 30] [--language uk]
```

**HTTP server (recommended for the macOS app):**
```bash
uv run mlx-nemotron serve [--host 127.0.0.1] [--port 8000]
# or directly:
python src/mlx_nemotron/server.py [--host 0.0.0.0] [--port 8000]
```

Once running:
```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/transcribe -F "file=@audio.m4a"
curl -X POST http://localhost:8000/transcribe/path \
     -H "Content-Type: application/json" \
     -d '{"path": "/abs/path/audio.m4a", "chunk_seconds": 30, "language": "uk"}'
curl http://localhost:8000/jobs/<job_id>
curl http://localhost:8000/jobs            # list all jobs
```

**macOS app:**
```bash
cd macos_app
open Package.swift   # opens in Xcode; build & run the NemotronApp target
```

**Tests:**
```bash
uv run pytest
```

## Architecture

```
src/mlx_nemotron/
├── core.py     — transcribe(), split_audio_cached(), load_model(), file_cache_key()
├── cli.py      — argparse entry point with `transcribe` and `serve` subcommands
└── server.py   — FastAPI server with /health, /transcribe, /transcribe/path, /jobs
tests/
├── conftest.py — shared fixtures: audio_file, chunks_dir, mock_model
├── test_core.py
├── test_cli.py
└── test_server.py

macos_app/
├── Package.swift
└── Sources/NemotronApp/
    ├── App/
    │   ├── NemotronApp.swift   — @main, scene + Settings, holds ServerManager/LibraryStore
    │   └── AppSettings.swift   — @UserDefault wrapper, resolvedBinaryPath search
    ├── Services/
    │   ├── ServerManager.swift     — spawns the Python server, polls /health
    │   ├── TranscribeService.swift — submits jobs, polls /jobs/<id>
    │   └── LibraryStore.swift      — GRDB-backed audio_records table + progress state
    ├── Models/
    │   └── AudioRecord.swift   — GRDB record (id, paths, status, language, jobId)
    └── Views/
        ├── ContentView.swift    — server-state gate + NavigationSplitView
        ├── DropZoneView.swift   — drag/drop & file picker for new audio
        ├── DropTargetView.swift — NSView bridge for Finder drag handling
        ├── LibraryView.swift    — sidebar list of records
        ├── SettingsView.swift   — project/binary path, port, default language
        └── TranscriptView.swift — progress UI + final transcript w/ copy/export
```

## How the macOS app connects to Nemotron

This is the key flow added in the latest changes. The Swift app does **not** call MLX directly — it boots the Python backend as a child process and talks to it over loopback HTTP.

### 1. Binary discovery (`AppSettings.resolvedBinaryPath`)

On launch the app looks for an `mlx-nemotron` executable in this order:
1. Explicit `binaryPath` from Settings (if the file exists).
2. `<projectPath>/.venv/bin/mlx-nemotron` where `projectPath` is set in Settings.
3. Common project locations: `~/Documents/code/mlx_nemotron_streaming`, `~/code/...`, `~/Developer/...`.
4. Global installs: `~/.local/bin`, `/usr/local/bin`, `/opt/homebrew/bin`.

If nothing is found, `ContentView` renders `SetupRequiredView` which prompts the user to open Settings and point at the repo. **No automatic install** — the user must have the `uv pip install -e .` venv on disk.

### 2. Server lifecycle (`ServerManager`)

`ServerManager` is a `@MainActor ObservableObject` with four states: `notConfigured`, `starting`, `ready`, `failed(String)`.

On `start()`:
1. Kills anything already holding `AppSettings.serverPort` (default `9876`) with `lsof -ti tcp:<port> | xargs kill -9`. This guarantees we own the port even after a crash.
2. Spawns the child process: `Process` with `executableURL = <resolved binary>` and `arguments = ["serve", "--port", "<port>"]`. stdout/stderr are routed to `FileHandle.nullDevice`.
3. The `serve` subcommand (`cli.py`) does `from mlx_nemotron.server import app; uvicorn.run(app, ...)`. Uvicorn's lifespan handler calls `load_model()` which downloads/loads `mlx-community/nemotron-3.5-asr-streaming-0.6b` into MLX. First boot can be slow (model download).
4. The Swift side polls `GET /health` every 500 ms for up to 60 attempts (30 s budget). On 2xx the state flips to `.ready`. Otherwise `.failed("Server did not start within 30s")`.
5. `process.terminationHandler` flips to `.failed("Server process exited unexpectedly")` unless the state was already `.ready` (so clean shutdown isn't reported as a crash).

`stop()` cancels the poll task and `process.terminate()`s. `restart()` is `stop()` + `start()` and is wired to the "Restart Server" button in Settings.

The app sets `applicationShouldTerminateAfterLastWindowClosed = false` so closing the window keeps the server running; `applicationShouldHandleReopen` brings the window back when the dock icon is clicked.

### 3. Submitting a job (`TranscribeService`)

When a user drops or picks an audio file, `DropZoneView.enqueue(_:)`:
1. Copies the file into `~/Library/Application Support/mlx-nemotron/audios/<uuid>.<ext>` (so deletions from the original location don't break the library).
2. Inserts an `AudioRecord` into GRDB with status `.pending`.
3. Calls `TranscribeService.submit(record:)`.

`TranscribeService.run(record:)` then:
1. POSTs to `http://127.0.0.1:<port>/transcribe/path` with JSON `{ "path": <absolute audio path>, "chunk_seconds": 30, "language": <optional BCP-47> }`.
2. Receives `{ "job_id": "<uuid>", "status": "pending" }`. Stores `jobId` on the record and flips status to `.transcribing`.
3. Starts polling `GET /jobs/<job_id>` every 2 s (up to 3600 iterations ≈ 2 hours).

On the Python side, `server.py` submits `_run_job` to a `ThreadPoolExecutor(max_workers=1)` — MLX holds the GPU exclusively, so concurrent jobs would just contend. The shared in-process `_model` is reused for every request (loaded once during the FastAPI lifespan).

### 4. Progress reporting

`_run_job` passes two callbacks into `transcribe()` and mutates the `_jobs[job_id]` dict:

- `split_progress_callback(fraction)` — fired during ffmpeg splitting. `core.py` parses `time=HH:MM:SS.ss` out of ffmpeg's stderr and divides by total duration from `ffprobe`. Updates `_jobs[job_id]["split_progress"]`.
- `progress_callback(done, total)` — fired after each chunk is transcribed. Updates `phase` to `"transcribing"` and the `chunks_done/chunks_total` counters.

`/jobs/<job_id>` returns this dict verbatim. The Swift `JobResponse` decodes `phase`, `split_progress`, `chunks_done`, `chunks_total`, `transcript`, `error`. `LibraryStore.setProgress(...)` stores it in `transcriptionProgress[recordId]`, and `TranscriptView.inProgressContent` renders either a splitting bar (during phase `"splitting"`) or a chunk-count bar + ETA (during phase `"transcribing"`). ETA is `elapsed / chunks_done * chunks_remaining`.

### 5. Completion

When `_jobs[job_id]["status"] == "done"`, the response carries `"transcript": <string>`. `TranscribeService` writes it to `~/Library/Application Support/mlx-nemotron/transcripts/<record_id>.txt`, sets `record.transcriptPath`, status `.done`. `TranscriptView.loadTranscript()` reads the file in `onAppear` / `onChange(of: status)` and shows it with Copy + Export toolbar buttons.

On `"status": "error"`, the error string is stored in `library.transcriptionErrors[recordId]` and surfaced in `errorView`.

## Key implementation details

- **Model cache**: stored in `.venv/hf_cache/` via `HF_HOME` env var set at import time in `core.py`. `HF_HUB_DISABLE_PROGRESS_BARS=1` suppresses HF download noise.
- **Chunk cache**: WAV chunks cached in `$TMPDIR/mlx_nemotron_chunks/<key>/` keyed by `sha256(path + size + mtime + chunk_seconds)[:16]`. Re-runs skip ffmpeg but always re-transcribe from cached chunks.
- **Model**: `mlx-community/nemotron-3.5-asr-streaming-0.6b`. `att_context_size=[56, 0]` is the causal streaming window passed to `model.generate(...)`.
- **Server concurrency**: executor is `max_workers=1` — MLX holds the GPU exclusively. Multiple POSTs queue up.
- **Job state is in-memory only**: `_jobs: dict[str, dict]` lives in the server process and is wiped on restart. The macOS app's GRDB library is the durable record of past transcriptions.
- **Language**: `None` = auto-detect; pass BCP-47 code (e.g. `"uk"`, `"en-US"`) to pin. Settings has a "Default language" field that's applied to every new record.
- **Default port**: server defaults to `8000`, but the macOS app overrides to `9876` to avoid colliding with common dev servers. Configurable in Settings.
- **Library locations** (macOS app):
  - DB: `~/Library/Application Support/mlx-nemotron/library.db` (GRDB / SQLite)
  - Audio originals: `~/Library/Application Support/mlx-nemotron/audios/<uuid>.<ext>`
  - Transcripts: `~/Library/Application Support/mlx-nemotron/transcripts/<record_id>.txt`

## Latest changes (since initial release)

- **`serve` subcommand** added to `cli.py` — `mlx-nemotron serve --port 9876` is what the macOS app spawns. The bare `mlx-nemotron <file>` form still works (CLI auto-prepends `transcribe`).
- **`/health` and `/jobs` endpoints** added to `server.py` so the Swift side can probe readiness and list all jobs.
- **Progress callbacks** (`progress_callback`, `split_progress_callback`) plumbed through `core.transcribe()` so the HTTP layer can publish split-phase % and chunk-phase counts without scraping stdout.
- **macOS SwiftUI companion app** (`macos_app/`):
  - Drag-and-drop / file picker ingestion with `DropTargetView` NSView bridge for Finder drags.
  - GRDB-backed library with persistent records, statuses, and language pinning.
  - Auto-spawned local server with health polling and port-conflict recovery.
  - Live splitting and chunk-transcription progress with elapsed time and ETA.
  - Copy-to-clipboard and `.txt` export of finished transcripts.
  - Settings panel for project path, binary override, server port, and default language.
