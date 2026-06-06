import argparse
import sys
from pathlib import Path

from mlx_nemotron.core import transcribe

_SUBCOMMANDS = {"transcribe", "serve", "-h", "--help"}


def main():
    # Allow bare `mlx-nemotron <file>` as shorthand for `mlx-nemotron transcribe <file>`
    if len(sys.argv) > 1 and sys.argv[1] not in _SUBCOMMANDS:
        sys.argv.insert(1, "transcribe")

    parser = argparse.ArgumentParser(
        prog="mlx-nemotron",
        description="Transcribe audio using mlx-community/nemotron-3.5-asr-streaming.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- transcribe ---
    transcribe_parser = subparsers.add_parser("transcribe", help="Transcribe an audio file")
    transcribe_parser.add_argument("audio_file", help="Path to the input audio file")
    transcribe_parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output transcript path (default: <stem>_transcript.txt beside input)",
    )
    transcribe_parser.add_argument(
        "--chunk-seconds",
        type=int,
        default=30,
        help="Duration of each audio chunk in seconds (default: 30)",
    )
    transcribe_parser.add_argument(
        "--language",
        default=None,
        help="BCP-47 language code, e.g. 'en-US', 'uk' (default: auto-detect)",
    )

    # --- serve ---
    serve_parser = subparsers.add_parser("serve", help="Start the HTTP transcription server")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    serve_parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")

    args = parser.parse_args()

    if args.command == "transcribe":
        if not Path(args.audio_file).exists():
            transcribe_parser.error(f"File not found: {args.audio_file}")
        transcribe(
            input_audio=args.audio_file,
            output_file=args.output,
            chunk_seconds=args.chunk_seconds,
            language=args.language,
        )

    elif args.command == "serve":
        import uvicorn
        from mlx_nemotron.server import app
        uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
