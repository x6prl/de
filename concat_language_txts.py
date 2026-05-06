#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import validate_format


DEFAULT_LANGUAGES = ("ar", "en", "ru", "tr")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Concatenate per-language .txt files into ar.txt, en.txt, ru.txt, and tr.txt."
    )
    parser.add_argument(
        "languages",
        nargs="*",
        default=list(DEFAULT_LANGUAGES),
        help="Language directories to process. Defaults to ar en ru tr.",
    )
    return parser.parse_args(argv)


def iter_source_files(language_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in language_dir.glob("*.txt")
        if path.is_file()
    )


def read_chunk(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n").strip()


def build_output(language: str, root: Path) -> Path:
    language_dir = root / language
    if not language_dir.is_dir():
        raise FileNotFoundError(f"language directory does not exist: {language_dir}")

    source_files = iter_source_files(language_dir)
    if not source_files:
        raise FileNotFoundError(f"no .txt files found in {language_dir}")

    chunks = [chunk for chunk in (read_chunk(path) for path in source_files) if chunk]
    if not chunks:
        raise ValueError(f"all .txt files in {language_dir} are empty")

    output_path = root / f"{language}.txt"
    output_path.write_text("\n\n".join(chunks) + "\n", encoding="utf-8")
    return output_path


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    root = Path(__file__).resolve().parent
    generated: list[Path] = []

    try:
        for language in args.languages:
            output_path = build_output(language, root)
            generated.append(output_path)
            print(f"Wrote {output_path.name}")
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    all_messages: list[validate_format.ValidationError] = []
    for output_path in generated:
        all_messages.extend(validate_format.validate_file(output_path))

    error_count = sum(1 for message in all_messages if message.severity == "error")
    warning_count = sum(1 for message in all_messages if message.severity == "warning")

    if all_messages:
        for message in all_messages:
            stream = sys.stderr if message.severity == "error" else sys.stdout
            print(message.render(), file=stream)

    if error_count:
        summary = f"{error_count} validation error(s)"
        if warning_count:
            summary += f", {warning_count} warning(s)"
        print(f"{summary} found across {len(generated)} generated file(s).", file=sys.stderr)
        return 1

    if warning_count:
        print(f"Validated {len(generated)} generated file(s); {warning_count} warning(s) found.")
        return 0

    print(f"Validated {len(generated)} generated file(s); no format errors found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
