#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


NOUN_PREFIXES = ("der ", "die ", "das ", "(-) ")
PLURAL_MARKER_RE = re.compile(r'^(?:\((?:sg|pl)\.\)|[-"][^\s]*)$')
VERB_SPLIT_RE = re.compile(r"\s*/\s*")
GRAMMAR_LINE_RE = re.compile(r"^\[(.*)\]$")
TRANSLATION_CUES_RE = re.compile(r"^(?P<gloss>.*\S)\{(?P<cues>[^{}]+)\}$")
TRANSLATION_CUE_ITEM_RE = re.compile(r"^(?P<tag>[a-z]{3})=(?P<value>.*\S)$")
KNOWN_CUE_TAGS = {"prs", "pst", "par", "aux", "cmp", "sup"}


@dataclass(frozen=True)
class ValidationError:
    path: Path
    line: int
    message: str

    def render(self) -> str:
        return f"{self.path}:{self.line}: {self.message}"


def iter_files(paths: list[str]) -> Iterable[Path]:
    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists():
            yield path
            continue
        if path.is_file():
            yield path
            continue
        if path.is_dir():
            for child in sorted(
                p for p in path.rglob("*") if p.is_file() and not any(part.startswith(".") for part in p.parts)
            ):
                yield child
            continue
        yield path


def read_lines(path: Path) -> tuple[list[str] | None, list[ValidationError]]:
    if not path.exists():
        return None, [ValidationError(path, 0, "path does not exist")]
    if not path.is_file():
        return None, [ValidationError(path, 0, "path is not a regular file")]

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return None, [ValidationError(path, exc.start + 1, "file is not valid UTF-8")]
    except OSError as exc:
        return None, [ValidationError(path, 0, f"could not read file: {exc}")]

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.split("\n"), []


def add_whitespace_error(errors: list[ValidationError], path: Path, line_no: int, line: str) -> str:
    stripped = line.strip()
    if line != stripped:
        errors.append(ValidationError(path, line_no, "line has leading or trailing whitespace"))
    return stripped


def validate_noun(path: Path, line_no: int, lemma: str) -> list[ValidationError]:
    errors: list[ValidationError] = []
    body = lemma[4:]
    if " " not in body:
        errors.append(ValidationError(path, line_no, "noun entry must include a lemma and a plural marker"))
        return errors

    noun, marker = body.rsplit(" ", 1)
    if not noun:
        errors.append(ValidationError(path, line_no, "noun lemma is empty"))
    if not marker:
        errors.append(ValidationError(path, line_no, "noun plural marker is empty"))
    elif not PLURAL_MARKER_RE.match(marker):
        errors.append(
            ValidationError(
                path,
                line_no,
                f"noun plural marker {marker!r} must look like a suffix or (sg.)/(pl.)",
            )
        )
    return errors


def validate_verb(path: Path, line_no: int, lemma: str) -> list[ValidationError]:
    errors: list[ValidationError] = []
    body = lemma[2:]
    if not body:
        return [ValidationError(path, line_no, "verb entry is missing verb data")]

    fields = VERB_SPLIT_RE.split(body)
    if len(fields) > 3:
        errors.append(ValidationError(path, line_no, "verb entry may contain at most 3 fields"))
        return errors

    if any(field == "" for field in fields):
        errors.append(ValidationError(path, line_no, "verb entry contains an empty field"))
        return errors

    first = fields[0]
    if "-" in first:
        infinitive, present_exception = first.split("-", 1)
        if not infinitive:
            errors.append(ValidationError(path, line_no, "verb infinitive is empty"))
        if not present_exception:
            errors.append(ValidationError(path, line_no, "verb present-tense exception is empty"))
    elif not first:
        errors.append(ValidationError(path, line_no, "verb infinitive is empty"))

    if len(fields) >= 2 and fields[1] == "":
        errors.append(ValidationError(path, line_no, "verb Prateritum field is empty"))
    if len(fields) == 3 and fields[2] == "":
        errors.append(ValidationError(path, line_no, "verb auxiliary/participle field is empty"))

    return errors


def validate_adjective(path: Path, line_no: int, lemma: str) -> list[ValidationError]:
    errors: list[ValidationError] = []
    body = lemma[2:]
    if not body:
        return [ValidationError(path, line_no, "adjective entry is missing adjective data")]

    parts = body.split()
    if len(parts) == 1:
        return errors
    if len(parts) == 2 and parts[1] == "(indecl.)":
        return errors
    if len(parts) >= 3 and parts[1] != "(indecl.)":
        return errors

    errors.append(
        ValidationError(
            path,
            line_no,
            "adjective entry must be `a lemma`, `a lemma (indecl.)`, or `a lemma comparative superlative`",
        )
    )
    return errors


def validate_lemma(path: Path, line_no: int, lemma: str) -> list[ValidationError]:
    if not lemma:
        return [ValidationError(path, line_no, "lemma line is empty")]
    if lemma.startswith(NOUN_PREFIXES):
        return validate_noun(path, line_no, lemma)
    if lemma.startswith("v "):
        return validate_verb(path, line_no, lemma)
    if lemma == "v":
        return [ValidationError(path, line_no, "verb entry is missing verb data")]
    if lemma.startswith("a "):
        return validate_adjective(path, line_no, lemma)
    if lemma == "a":
        return [ValidationError(path, line_no, "adjective entry is missing adjective data")]
    return []


def validate_translation(path: Path, line_no: int, lemma: str, translation: str) -> list[ValidationError]:
    errors: list[ValidationError] = []
    if not translation:
        return [ValidationError(path, line_no, "translation line is empty")]

    parts = [part.strip() for part in translation.split(";")]
    if parts and parts[-1] == "":
        parts = parts[:-1]

    if not parts:
        errors.append(ValidationError(path, line_no, "translation line must contain at least one translation"))
        return errors

    for part in parts:
        if not part:
            errors.append(ValidationError(path, line_no, "translation line contains an empty translation item"))
            break
        if "{" not in part and "}" not in part:
            continue

        match = TRANSLATION_CUES_RE.match(part)
        if not match:
            errors.append(
                ValidationError(
                    path,
                    line_no,
                    "translation reverse-cue block must be `gloss{tag=value, tag=value}` at the end of a translation item",
                )
            )
            break

        gloss = match.group("gloss").strip()
        if not gloss:
            errors.append(ValidationError(path, line_no, "translation item with reverse cues must include a gloss"))
            break

        cues = [cue.strip() for cue in match.group("cues").split(",")]
        if any(cue == "" for cue in cues):
            errors.append(ValidationError(path, line_no, "translation reverse-cue list contains an empty cue"))
            break

        seen_tags: set[str] = set()
        for cue in cues:
            cue_match = TRANSLATION_CUE_ITEM_RE.match(cue)
            if not cue_match:
                errors.append(
                    ValidationError(
                        path,
                        line_no,
                        "translation reverse-cue item must be `tag=value` with a 3-letter lowercase ASCII tag",
                    )
                )
                break

            tag = cue_match.group("tag")
            value = cue_match.group("value").strip()
            if tag not in KNOWN_CUE_TAGS:
                errors.append(
                    ValidationError(
                        path,
                        line_no,
                        f"translation reverse-cue tag {tag!r} is unknown; use one of {sorted(KNOWN_CUE_TAGS)!r}",
                    )
                )
                break

            if tag == "prs" and "/" in value:
                errors.append(
                    ValidationError(
                        path,
                        line_no,
                        "translation `prs=` cue must contain a single third-person present form, not multiple forms",
                    )
                )
                break

            if lemma.startswith("v ") and tag in {"cmp", "sup"}:
                errors.append(
                    ValidationError(
                        path,
                        line_no,
                        f"verb translation item cannot use adjective cue tag {tag!r}",
                    )
                )
                break

            if lemma.startswith("a ") and tag in {"prs", "pst", "par", "aux"}:
                errors.append(
                    ValidationError(
                        path,
                        line_no,
                        f"adjective translation item cannot use verb cue tag {tag!r}",
                    )
                )
                break

            if tag in seen_tags:
                errors.append(
                    ValidationError(
                        path,
                        line_no,
                        f"translation reverse-cue list contains duplicate tag {tag!r}",
                    )
                )
                break
            seen_tags.add(tag)
        else:
            continue
        break

    return errors


def validate_grammar(path: Path, line_no: int, grammar: str) -> list[ValidationError]:
    match = GRAMMAR_LINE_RE.match(grammar)
    if not match:
        return [ValidationError(path, line_no, "grammar line must be enclosed in `[` and `]`")]

    inner = match.group(1).strip()
    if not inner:
        return [ValidationError(path, line_no, "grammar line is empty")]

    parts = [part.strip() for part in inner.split(";")]
    if any(part == "" for part in parts):
        return [ValidationError(path, line_no, "grammar line contains an empty grammar item")]

    return []


def validate_file(path: Path) -> list[ValidationError]:
    lines, errors = read_lines(path)
    if lines is None:
        return errors

    index = 0
    total = len(lines)
    while index < total:
        raw_line = lines[index]
        line_no = index + 1
        stripped = add_whitespace_error(errors, path, line_no, raw_line)

        if stripped == "":
            index += 1
            continue

        lemma_line = stripped
        if GRAMMAR_LINE_RE.match(lemma_line):
            errors.append(
                ValidationError(path, line_no, "grammar line is only allowed directly after a translation line")
            )
        errors.extend(validate_lemma(path, line_no, lemma_line))

        index += 1
        if index >= total:
            errors.append(ValidationError(path, line_no, "entry is missing a translation line"))
            break

        raw_translation = lines[index]
        translation_line_no = index + 1
        translation = add_whitespace_error(errors, path, translation_line_no, raw_translation)
        errors.extend(validate_translation(path, translation_line_no, lemma_line, translation))
        index += 1

        if translation == "":
            continue

        if index < total:
            raw_grammar = lines[index]
            grammar_line_no = index + 1
            grammar = add_whitespace_error(errors, path, grammar_line_no, raw_grammar)
            if grammar != "" and GRAMMAR_LINE_RE.match(grammar):
                errors.extend(validate_grammar(path, grammar_line_no, grammar))
                index += 1

        while index < total:
            raw_trailing = lines[index]
            trailing_line_no = index + 1
            trailing = add_whitespace_error(errors, path, trailing_line_no, raw_trailing)
            if trailing == "":
                break
            if GRAMMAR_LINE_RE.match(trailing):
                errors.append(
                    ValidationError(
                        path,
                        trailing_line_no,
                        "grammar line is only allowed directly after a translation line",
                    )
                )
            else:
                errors.append(
                    ValidationError(
                        path,
                        trailing_line_no,
                        "extra entry line is not allowed; store translatable examples as separate phrase entries",
                    )
                )
            index += 1

        if index < total and lines[index].strip() == "":
            index += 1

    return errors


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate dictionary files against format.md.")
    parser.add_argument(
        "paths",
        nargs="*",
        default=["en", "ru"],
        help="Files or directories to validate. Directories are scanned recursively.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    all_errors: list[ValidationError] = []
    validated_files = 0

    for path in iter_files(args.paths):
        file_errors = validate_file(path)
        all_errors.extend(file_errors)
        if path.exists() and path.is_file():
            validated_files += 1

    if all_errors:
        for error in all_errors:
            print(error.render(), file=sys.stderr)
        print(f"{len(all_errors)} error(s) found across {validated_files} file(s).", file=sys.stderr)
        return 1

    print(f"Validated {validated_files} file(s); no format errors found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
