import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from mlx_nemotron.core import (
    file_cache_key,
    format_time,
    get_chunks_cache_dir,
    split_audio_cached,
    transcribe,
)


# ---------- format_time ----------

def test_format_time_seconds():
    assert format_time(45) == "45s"

def test_format_time_minutes():
    assert format_time(125) == "2m 5s"

def test_format_time_hours():
    assert format_time(3661) == "1h 1m 1s"

def test_format_time_zero():
    assert format_time(0) == "0s"


# ---------- file_cache_key ----------

def test_file_cache_key_deterministic(audio_file):
    assert file_cache_key(audio_file, 30) == file_cache_key(audio_file, 30)

def test_file_cache_key_length(audio_file):
    assert len(file_cache_key(audio_file, 30)) == 16

def test_file_cache_key_changes_with_chunk_seconds(audio_file):
    assert file_cache_key(audio_file, 30) != file_cache_key(audio_file, 10)

def test_file_cache_key_changes_with_content(tmp_path):
    f1 = tmp_path / "a.m4a"
    f2 = tmp_path / "b.m4a"
    f1.write_bytes(b"x" * 100)
    f2.write_bytes(b"y" * 100)
    # different files → different keys (mtime may differ; size same but path differs)
    assert file_cache_key(f1, 30) != file_cache_key(f2, 30)


# ---------- split_audio_cached ----------

def test_split_audio_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        split_audio_cached(str(tmp_path / "missing.m4a"))

def test_split_audio_cache_hit(audio_file, mock_model):
    chunks_dir = get_chunks_cache_dir(str(audio_file), 30)
    chunks_dir.mkdir(parents=True, exist_ok=True)
    (chunks_dir / "chunk_000.wav").write_bytes(b"")
    (chunks_dir / "chunk_001.wav").write_bytes(b"")

    with patch("subprocess.run") as mock_run:
        result = split_audio_cached(str(audio_file), chunk_seconds=30)
        mock_run.assert_not_called()

    assert result == chunks_dir

def test_split_audio_runs_ffmpeg(audio_file):
    chunks_dir = get_chunks_cache_dir(str(audio_file), 30)

    def fake_ffmpeg(cmd, **kwargs):
        chunks_dir.mkdir(parents=True, exist_ok=True)
        (chunks_dir / "chunk_000.wav").write_bytes(b"")
        (chunks_dir / "chunk_001.wav").write_bytes(b"")
        r = MagicMock()
        r.returncode = 0
        return r

    with patch("subprocess.run", side_effect=fake_ffmpeg):
        result = split_audio_cached(str(audio_file), chunk_seconds=30)

    assert result == chunks_dir
    assert len(sorted(result.glob("chunk_*.wav"))) == 2

def test_split_audio_ffmpeg_failure(audio_file):
    r = MagicMock()
    r.returncode = 1
    r.stderr = "ffmpeg: error"

    with patch("subprocess.run", return_value=r):
        with pytest.raises(RuntimeError, match="FFmpeg failed"):
            split_audio_cached(str(audio_file))

def test_split_audio_ffmpeg_no_chunks(audio_file):
    chunks_dir = get_chunks_cache_dir(str(audio_file), 30)

    def fake_ffmpeg(cmd, **kwargs):
        chunks_dir.mkdir(parents=True, exist_ok=True)
        r = MagicMock()
        r.returncode = 0
        return r

    with patch("subprocess.run", side_effect=fake_ffmpeg):
        with pytest.raises(RuntimeError, match="no chunks were created"):
            split_audio_cached(str(audio_file))


# ---------- transcribe ----------

def test_transcribe_joins_chunk_texts(audio_file, chunks_dir, mock_model):
    mock_model.generate.side_effect = [
        MagicMock(text="one"),
        MagicMock(text="two"),
        MagicMock(text="three"),
    ]

    with patch("mlx_nemotron.core.split_audio_cached", return_value=chunks_dir):
        result = transcribe(str(audio_file), output_file="", model=mock_model)

    assert result == "one\ntwo\nthree"

def test_transcribe_strips_whitespace(audio_file, tmp_path, mock_model):
    d = tmp_path / "c"
    d.mkdir()
    (d / "chunk_000.wav").write_bytes(b"")
    mock_model.generate.return_value = MagicMock(text="  hello  ")

    with patch("mlx_nemotron.core.split_audio_cached", return_value=d):
        result = transcribe(str(audio_file), output_file="", model=mock_model)

    assert result == "hello"

def test_transcribe_writes_output(audio_file, chunks_dir, mock_model, tmp_path):
    out = tmp_path / "out.txt"
    mock_model.generate.return_value = MagicMock(text="text")

    with patch("mlx_nemotron.core.split_audio_cached", return_value=chunks_dir):
        transcribe(str(audio_file), output_file=str(out), model=mock_model)

    assert out.read_text(encoding="utf-8") == "text\ntext\ntext"

def test_transcribe_default_output_path(tmp_path, chunks_dir, mock_model):
    audio = tmp_path / "interview.m4a"
    audio.write_bytes(b"fake")
    mock_model.generate.return_value = MagicMock(text="x")

    with patch("mlx_nemotron.core.split_audio_cached", return_value=chunks_dir):
        transcribe(str(audio), model=mock_model)

    assert (tmp_path / "interview_transcript.txt").exists()

def test_transcribe_passes_language(audio_file, tmp_path, mock_model):
    d = tmp_path / "c"
    d.mkdir()
    (d / "chunk_000.wav").write_bytes(b"")
    mock_model.generate.return_value = MagicMock(text="Привіт")

    with patch("mlx_nemotron.core.split_audio_cached", return_value=d):
        transcribe(str(audio_file), output_file="", language="uk", model=mock_model)

    assert mock_model.generate.call_args[1].get("language") == "uk"

def test_transcribe_no_language_kwarg_when_none(audio_file, tmp_path, mock_model):
    d = tmp_path / "c"
    d.mkdir()
    (d / "chunk_000.wav").write_bytes(b"")
    mock_model.generate.return_value = MagicMock(text="hi")

    with patch("mlx_nemotron.core.split_audio_cached", return_value=d):
        transcribe(str(audio_file), output_file="", language=None, model=mock_model)

    assert "language" not in mock_model.generate.call_args[1]

def test_transcribe_loads_model_when_none(audio_file, chunks_dir):
    mock_model = MagicMock()
    mock_model.generate.return_value = MagicMock(text="hi")

    with patch("mlx_nemotron.core.split_audio_cached", return_value=chunks_dir):
        with patch("mlx_nemotron.core.load_model", return_value=mock_model) as mock_load:
            transcribe(str(audio_file), output_file="")
            mock_load.assert_called_once()
