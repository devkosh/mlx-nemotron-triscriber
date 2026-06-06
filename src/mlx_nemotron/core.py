import os
from pathlib import Path
from time import perf_counter
import hashlib
import subprocess
import tempfile

_PROJECT_ROOT = Path(__file__).parent.parent.parent
os.environ.setdefault("HF_HOME", str(_PROJECT_ROOT / ".venv" / "hf_cache"))
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")

from mlx_audio.stt import load
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.panel import Panel
from rich.table import Table

console = Console()

MODEL_ID = "mlx-community/nemotron-3.5-asr-streaming-0.6b"


def format_time(seconds: float) -> str:
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def file_cache_key(input_file: Path, chunk_seconds: int) -> str:
    stat = input_file.stat()
    raw = f"{input_file.resolve()}:{stat.st_size}:{stat.st_mtime}:{chunk_seconds}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def get_chunks_cache_dir(input_file: str, chunk_seconds: int) -> Path:
    input_path = Path(input_file)
    cache_root = Path(tempfile.gettempdir()) / "mlx_nemotron_chunks"
    cache_key = file_cache_key(input_path, chunk_seconds)
    return cache_root / cache_key


def split_audio_cached(input_file: str, chunk_seconds: int = 30) -> Path:
    input_path = Path(input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    chunks_dir = get_chunks_cache_dir(input_file, chunk_seconds)
    chunks_dir.mkdir(parents=True, exist_ok=True)

    existing_chunks = sorted(chunks_dir.glob("chunk_*.wav"))
    if existing_chunks:
        console.print(f"[dim]Using cached chunks ({len(existing_chunks)} found)[/dim]")
        return chunks_dir

    with console.status("[bold cyan]Splitting audio with ffmpeg…[/bold cyan]"):
        output_pattern = chunks_dir / "chunk_%03d.wav"
        cmd = [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-ar", "16000",
            "-ac", "1",
            "-f", "segment",
            "-segment_time", str(chunk_seconds),
            "-c:a", "pcm_s16le",
            str(output_pattern),
        ]
        result = subprocess.run(cmd, text=True, capture_output=True)

    if result.returncode != 0:
        console.print(result.stderr, style="red")
        raise RuntimeError("FFmpeg failed")

    chunks = sorted(chunks_dir.glob("chunk_*.wav"))
    if not chunks:
        raise RuntimeError("FFmpeg finished, but no chunks were created")

    console.print(f"[green]✓[/green] Split into [bold]{len(chunks)}[/bold] chunks")
    return chunks_dir


def load_model():
    with console.status("[bold cyan]Loading model…[/bold cyan]"):
        start = perf_counter()
        model = load(MODEL_ID)
    console.print(f"[green]✓[/green] Model loaded in [bold]{format_time(perf_counter() - start)}[/bold]")
    return model


def transcribe(
    input_audio: str,
    output_file: str | None = None,
    chunk_seconds: int = 30,
    language: str | None = None,
    model=None,
) -> str:
    """
    Transcribe an audio file and return the transcript as a string.

    Args:
        input_audio: Path to the input audio file (any ffmpeg-supported format).
        output_file: Path to write the transcript. Defaults to <stem>_transcript.txt
                     beside the input file. Pass empty string "" to skip writing.
        chunk_seconds: Duration of each WAV chunk for splitting.
        language: BCP-47 language code (e.g. "en-US", "uk"). None = auto-detect.
        model: Pre-loaded mlx_audio model. If None, loads internally.
    """
    total_start = perf_counter()
    input_path = Path(input_audio)

    if output_file is None:
        output_file = str(input_path.parent / f"{input_path.stem}_transcript.txt")

    console.rule("[bold]mlx-nemotron transcription[/bold]")
    console.print(f"[dim]Input:[/dim]  {input_path.name}")
    console.print(f"[dim]Output:[/dim] {output_file or '—'}")
    console.print(f"[dim]Lang:[/dim]   {language or 'auto-detect'}\n")

    chunks_dir = split_audio_cached(input_audio, chunk_seconds=chunk_seconds)

    if model is None:
        model = load_model()

    chunks = sorted(chunks_dir.glob("chunk_*.wav"))
    texts = []

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}[/bold cyan]"),
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        TextColumn("[dim]eta[/dim]"),
        TimeRemainingColumn(),
        console=console,
    )

    with progress:
        task = progress.add_task("Transcribing", total=len(chunks))
        for chunk in chunks:
            kwargs = {"att_context_size": [56, 0]}
            if language:
                kwargs["language"] = language
            result = model.generate(str(chunk), **kwargs)
            texts.append(result.text.strip())
            progress.advance(task)

    transcript = "\n".join(texts)

    if output_file:
        Path(output_file).write_text(transcript, encoding="utf-8")

    total_elapsed = perf_counter() - total_start
    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="dim")
    summary.add_column(style="bold green")
    summary.add_row("Chunks", str(len(chunks)))
    summary.add_row("Total time", format_time(total_elapsed))
    summary.add_row("Saved to", output_file or "—")

    console.print()
    console.print(Panel(summary, title="[bold green]Done[/bold green]", border_style="green"))

    return transcript
