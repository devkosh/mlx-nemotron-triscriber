import argparse
import shutil
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from mlx_nemotron.core import load_model, transcribe

_model = None
_executor: ThreadPoolExecutor | None = None
_jobs: dict[str, dict] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _model, _executor
    _model = load_model()
    _executor = ThreadPoolExecutor(max_workers=1)
    yield
    _executor.shutdown(wait=True)


app = FastAPI(title="mlx-nemotron transcription server", lifespan=lifespan)


class PathRequest(BaseModel):
    path: str
    chunk_seconds: int = 30
    language: Optional[str] = None


def _run_job(job_id: str, audio_path: str, chunk_seconds: int, language, cleanup_path=None):
    try:
        transcript = transcribe(
            input_audio=audio_path,
            output_file=None,
            chunk_seconds=chunk_seconds,
            language=language,
            model=_model,
        )
        _jobs[job_id] = {"status": "done", "transcript": transcript}
    except Exception as exc:
        _jobs[job_id] = {"status": "error", "error": str(exc)}
    finally:
        if cleanup_path:
            shutil.rmtree(cleanup_path, ignore_errors=True)


@app.post("/transcribe")
async def transcribe_file(file: Optional[UploadFile] = File(default=None)):
    """Upload an audio file for transcription. Returns a job_id to poll."""
    if file is None:
        raise HTTPException(status_code=422, detail="Provide a file via multipart or use POST /transcribe/path")

    tmp_dir = Path(tempfile.mkdtemp())
    suffix = Path(file.filename).suffix if file.filename else ".audio"
    tmp_path = tmp_dir / f"upload{suffix}"
    tmp_path.write_bytes(await file.read())

    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "pending"}
    _executor.submit(_run_job, job_id, str(tmp_path), 30, None, str(tmp_dir))

    return {"job_id": job_id, "status": "pending"}


@app.post("/transcribe/path")
async def transcribe_path(req: PathRequest):
    """Transcribe a file already on disk by absolute path."""
    if not Path(req.path).exists():
        raise HTTPException(status_code=404, detail=f"File not found: {req.path}")

    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "pending"}
    _executor.submit(_run_job, job_id, req.path, req.chunk_seconds, req.language)

    return {"job_id": job_id, "status": "pending"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/jobs")
async def list_jobs():
    return JSONResponse(content=_jobs)


@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JSONResponse(content=job)


if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser(description="mlx-nemotron transcription HTTP server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port)
