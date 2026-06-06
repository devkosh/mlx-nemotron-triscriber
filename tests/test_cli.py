import pytest
from unittest.mock import patch


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


def test_calls_transcribe_with_defaults(tmp_path):
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


def test_calls_transcribe_with_all_flags(tmp_path):
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
