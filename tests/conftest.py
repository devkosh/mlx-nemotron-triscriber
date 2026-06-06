import pytest
from pathlib import Path
from unittest.mock import MagicMock


@pytest.fixture
def audio_file(tmp_path) -> Path:
    f = tmp_path / "audio.m4a"
    f.write_bytes(b"fake audio data")
    return f


@pytest.fixture
def chunks_dir(tmp_path) -> Path:
    d = tmp_path / "chunks"
    d.mkdir()
    for i in range(3):
        (d / f"chunk_{i:03d}.wav").write_bytes(b"")
    return d


@pytest.fixture
def mock_model():
    model = MagicMock()
    model.generate.return_value = MagicMock(text="hello")
    return model
