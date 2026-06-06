import pytest
from unittest.mock import patch, MagicMock


def test_missing_file_exits_nonzero(tmp_path, capsys):
    with patch("sys.argv", ["mlx-nemotron", str(tmp_path / "missing.m4a")]):
        with pytest.raises(SystemExit) as exc:
            from mlx_nemotron.cli import main
            main()
    assert exc.value.code != 0


def test_help_exits_zero():
    with patch("sys.argv", ["mlx-nemotron", "--help"]):
        with pytest.raises(SystemExit) as exc:
            from mlx_nemotron.cli import main
            main()
    assert exc.value.code == 0


# --- implicit `mlx-nemotron <file>` (no subcommand) ---

def test_bare_file_calls_transcribe(tmp_path):
    audio = tmp_path / "audio.m4a"
    audio.write_bytes(b"fake")

    with patch("sys.argv", ["mlx-nemotron", str(audio)]):
        with patch("mlx_nemotron.cli.transcribe") as mock_t:
            from mlx_nemotron.cli import main
            main()

    mock_t.assert_called_once_with(
        input_audio=str(audio),
        output_file=None,
        chunk_seconds=30,
        language=None,
    )


def test_bare_file_with_flags(tmp_path):
    audio = tmp_path / "audio.m4a"
    audio.write_bytes(b"fake")
    out = str(tmp_path / "out.txt")

    with patch("sys.argv", ["mlx-nemotron", str(audio), "--output", out, "--chunk-seconds", "15", "--language", "uk"]):
        with patch("mlx_nemotron.cli.transcribe") as mock_t:
            from mlx_nemotron.cli import main
            main()

    mock_t.assert_called_once_with(
        input_audio=str(audio),
        output_file=out,
        chunk_seconds=15,
        language="uk",
    )


# --- explicit `mlx-nemotron transcribe <file>` ---

def test_explicit_transcribe_subcommand(tmp_path):
    audio = tmp_path / "audio.m4a"
    audio.write_bytes(b"fake")

    with patch("sys.argv", ["mlx-nemotron", "transcribe", str(audio)]):
        with patch("mlx_nemotron.cli.transcribe") as mock_t:
            from mlx_nemotron.cli import main
            main()

    mock_t.assert_called_once_with(
        input_audio=str(audio),
        output_file=None,
        chunk_seconds=30,
        language=None,
    )


# --- `mlx-nemotron serve` ---

def test_serve_subcommand_calls_uvicorn(tmp_path):
    mock_uvicorn = MagicMock()

    with patch("sys.argv", ["mlx-nemotron", "serve", "--host", "0.0.0.0", "--port", "9000"]):
        with patch("mlx_nemotron.cli.uvicorn", mock_uvicorn, create=True):
            with patch("mlx_nemotron.cli.sys.argv", ["mlx-nemotron", "serve", "--host", "0.0.0.0", "--port", "9000"]):
                with patch("mlx_nemotron.server.load_model", return_value=MagicMock()):
                    import uvicorn as uv
                    with patch.object(uv, "run") as mock_run:
                        from mlx_nemotron.cli import main
                        main()
                        mock_run.assert_called_once()
                        _, kwargs = mock_run.call_args
                        assert kwargs.get("host") == "0.0.0.0"
                        assert kwargs.get("port") == 9000
