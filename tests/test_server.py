import time
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def clear_jobs():
    import mlx_nemotron.server as srv
    srv._jobs.clear()
    yield
    srv._jobs.clear()


@pytest.fixture
def client():
    with patch("mlx_nemotron.server.load_model", return_value=MagicMock()):
        from mlx_nemotron.server import app
        with TestClient(app) as c:
            yield c


def _wait_for_job(client, job_id, timeout=3.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = client.get(f"/jobs/{job_id}")
        if r.json()["status"] != "pending":
            return r.json()
        time.sleep(0.05)
    return client.get(f"/jobs/{job_id}").json()


# ---------- /jobs ----------

def test_get_unknown_job(client):
    assert client.get("/jobs/does-not-exist").status_code == 404


# ---------- /transcribe/path ----------

def test_transcribe_path_file_not_found(client):
    resp = client.post("/transcribe/path", json={"path": "/no/such/file.m4a"})
    assert resp.status_code == 404


def test_transcribe_path_returns_job_id(tmp_path, client):
    audio = tmp_path / "audio.m4a"
    audio.write_bytes(b"fake")

    with patch("mlx_nemotron.server.transcribe", return_value="hello"):
        resp = client.post("/transcribe/path", json={"path": str(audio)})

    assert resp.status_code == 200
    body = resp.json()
    assert "job_id" in body
    assert body["status"] == "pending"


def test_transcribe_path_job_completes(tmp_path, client):
    audio = tmp_path / "audio.m4a"
    audio.write_bytes(b"fake")

    with patch("mlx_nemotron.server.transcribe", return_value="hello world"):
        resp = client.post("/transcribe/path", json={"path": str(audio)})
        job = _wait_for_job(client, resp.json()["job_id"])

    assert job["status"] == "done"
    assert job["transcript"] == "hello world"


def test_transcribe_path_passes_language(tmp_path, client):
    audio = tmp_path / "audio.m4a"
    audio.write_bytes(b"fake")

    with patch("mlx_nemotron.server.transcribe", return_value="Привіт") as mock_t:
        resp = client.post("/transcribe/path", json={"path": str(audio), "language": "uk"})
        _wait_for_job(client, resp.json()["job_id"])

    assert mock_t.call_args[1]["language"] == "uk"


def test_transcribe_path_error_captured(tmp_path, client):
    audio = tmp_path / "audio.m4a"
    audio.write_bytes(b"fake")

    with patch("mlx_nemotron.server.transcribe", side_effect=RuntimeError("ffmpeg broke")):
        resp = client.post("/transcribe/path", json={"path": str(audio)})
        job = _wait_for_job(client, resp.json()["job_id"])

    assert job["status"] == "error"
    assert "ffmpeg broke" in job["error"]


# ---------- /transcribe (upload) ----------

def test_transcribe_upload_returns_job_id(tmp_path, client):
    audio = tmp_path / "audio.m4a"
    audio.write_bytes(b"fake audio bytes")

    with patch("mlx_nemotron.server.transcribe", return_value="uploaded"):
        with open(audio, "rb") as f:
            resp = client.post("/transcribe", files={"file": ("audio.m4a", f, "audio/mp4")})

    assert resp.status_code == 200
    assert "job_id" in resp.json()


def test_transcribe_upload_job_completes(tmp_path, client):
    audio = tmp_path / "audio.m4a"
    audio.write_bytes(b"fake audio bytes")

    with patch("mlx_nemotron.server.transcribe", return_value="uploaded result"):
        with open(audio, "rb") as f:
            resp = client.post("/transcribe", files={"file": ("audio.m4a", f, "audio/mp4")})
        job = _wait_for_job(client, resp.json()["job_id"])

    assert job["status"] == "done"
    assert job["transcript"] == "uploaded result"


def test_transcribe_no_file_returns_422(client):
    resp = client.post("/transcribe")
    assert resp.status_code == 422
