import argparse
from pathlib import Path

from mlx_nemotron.core import transcribe


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe an audio file using mlx-community/nemotron-3.5-asr-streaming."
    )
    parser.add_argument("audio_file", help="Path to the input audio file")
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output transcript path (default: <stem>_transcript.txt beside input)",
    )
    parser.add_argument(
        "--chunk-seconds",
        type=int,
        default=30,
        help="Duration of each audio chunk in seconds (default: 30)",
    )
    parser.add_argument(
        "--language",
        default=None,
        help="BCP-47 language code, e.g. 'en-US', 'uk' (default: auto-detect)",
    )

    args = parser.parse_args()

    if not Path(args.audio_file).exists():
        parser.error(f"File not found: {args.audio_file}")

    transcribe(
        input_audio=args.audio_file,
        output_file=args.output,
        chunk_seconds=args.chunk_seconds,
        language=args.language,
    )


if __name__ == "__main__":
    main()
