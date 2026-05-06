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
VERB_VARIANT_SPLIT_RE = re.compile(r"\s*,\s*")
GRAMMAR_LINE_RE = re.compile(r"^\[(.*)\]$")
TRANSLATION_CUES_RE = re.compile(r"^(?P<gloss>.*\S)\{(?P<cues>[^{}]+)\}$")
TRANSLATION_CUE_ITEM_RE = re.compile(r"^(?P<tag>[a-z]{3})=(?P<value>.*\S)$")
KNOWN_CUE_TAGS = {"prs", "pst", "par", "aux", "cmp", "sup"}
SEPARABLE_PREFIXES = (
    "zurecht",
    "zurück",
    "zusammen",
    "weiter",
    "hinweg",
    "vorbei",
    "gegenüber",
    "empor",
    "entgegen",
    "heraus",
    "herein",
    "herbei",
    "heran",
    "hinauf",
    "hinaus",
    "hinein",
    "voran",
    "weg",
    "bei",
    "dar",
    "ein",
    "fern",
    "fest",
    "fort",
    "heim",
    "her",
    "hin",
    "los",
    "mit",
    "nach",
    "preis",
    "statt",
    "teil",
    "um",
    "unter",
    "vor",
    "weg",
    "wieder",
    "zu",
    "ab",
    "an",
    "auf",
    "aus",
)
INSEPARABLE_PREFIXES = ("be", "emp", "ent", "er", "ge", "miss", "ver", "zer")
EPENTHETIC_E_RE = re.compile(r"(?:[dt]|[^aeiouäöüy][mn]|chn|ffn)$")


@dataclass(frozen=True)
class ValidationError:
    path: Path
    line: int
    message: str
    severity: str = "error"

    def render(self) -> str:
        return f"{self.path}:{self.line}: {self.severity}: {self.message}"


@dataclass(frozen=True)
class DuplicateEntryRecord:
    path: Path
    line: int
    head: str
    signature: tuple[str, ...]
    lemma: str


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
    elif " " in noun:
        errors.append(ValidationError(path, line_no, "noun lemma must be a single token; multi-word nouns are not allowed"))
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
        elif infinitive:
            regular_present = build_regular_present_forms(infinitive)
            present_variants = split_variants(present_exception)
            if present_variants and all(variant in regular_present for variant in present_variants):
                errors.append(
                    ValidationError(
                        path,
                        line_no,
                        "verb present-tense exception stores only regular forms; omit the exception block",
                        severity="warning",
                    )
                )
    elif not first:
        errors.append(ValidationError(path, line_no, "verb infinitive is empty"))
    else:
        infinitive = first

    if len(fields) >= 2 and fields[1] == "":
        errors.append(ValidationError(path, line_no, "verb Prateritum field is empty"))
    elif len(fields) >= 2 and fields[1] != "-" and first:
        regular_praeteritum = build_regular_praeteritum_forms(infinitive)
        praeteritum_variants = split_variants(fields[1])
        if praeteritum_variants and all(variant in regular_praeteritum for variant in praeteritum_variants):
            errors.append(
                ValidationError(
                    path,
                    line_no,
                    "verb Prateritum field stores only regular forms; use `-` instead",
                    severity="warning",
                )
            )
    if len(fields) == 3 and fields[2] == "":
        errors.append(ValidationError(path, line_no, "verb auxiliary/participle field is empty"))
    elif len(fields) == 3 and first:
        regular_participle = build_regular_participle_forms(infinitive)
        explicit_participle = extract_explicit_participle(fields[2])
        if explicit_participle in regular_participle:
            errors.append(
                ValidationError(
                    path,
                    line_no,
                    "verb auxiliary/participle field stores a regular participle; keep only the auxiliary",
                    severity="warning",
                )
            )

    return errors


def split_variants(value: str) -> list[str]:
    return [part.strip() for part in VERB_VARIANT_SPLIT_RE.split(value) if part.strip()]


def split_infinitive(infinitive: str) -> tuple[bool, str, str]:
    reflexive = infinitive.startswith("sich ")
    core = infinitive[5:] if reflexive else infinitive
    for prefix in SEPARABLE_PREFIXES:
        if core.startswith(prefix) and len(core) > len(prefix) + 1:
            base = core[len(prefix) :]
            if base.endswith(("en", "n")):
                return reflexive, prefix, base
    return reflexive, "", core


def needs_epenthetic_e(stem: str) -> bool:
    return bool(EPENTHETIC_E_RE.search(stem))


def build_regular_stem(base: str) -> tuple[str, bool]:
    if base.endswith(("eln", "ern")):
        return base[:-1], False
    if base.endswith("en"):
        return base[:-2], needs_epenthetic_e(base[:-2])
    if base.endswith("n"):
        return base[:-1], False
    return base, False


def build_regular_present_forms(infinitive: str) -> set[str]:
    reflexive, prefix, base = split_infinitive(infinitive)
    stem, add_e = build_regular_stem(base)
    finite = stem + ("et" if add_e else "t")
    return {compose_surface_form(finite, prefix, reflexive)}


def build_regular_praeteritum_forms(infinitive: str) -> set[str]:
    reflexive, prefix, base = split_infinitive(infinitive)
    stem, add_e = build_regular_stem(base)
    finite = stem + ("ete" if add_e else "te")
    return {compose_surface_form(finite, prefix, reflexive)}


def build_regular_participle_forms(infinitive: str) -> set[str]:
    reflexive, prefix, base = split_infinitive(infinitive)
    stem, add_e = build_regular_stem(base)
    participle_core = stem + ("et" if add_e else "t")
    if base.endswith("ieren") or any(base.startswith(item) for item in INSEPARABLE_PREFIXES):
        participle = base[:-2] + "t" if base.endswith("ieren") else participle_core
    else:
        participle = "ge" + participle_core
    if prefix:
        participle = prefix + participle
    forms = {participle}
    if reflexive:
        forms.add(f"sich {participle}")
    return forms


def compose_surface_form(finite: str, prefix: str, reflexive: bool) -> str:
    parts = [finite]
    if reflexive:
        parts.append("sich")
    if prefix:
        parts.append(prefix)
    return " ".join(parts)


def extract_explicit_participle(auxiliary_field: str) -> str | None:
    for prefix in ("hat ", "ist "):
        if auxiliary_field.startswith(prefix):
            remainder = auxiliary_field[len(prefix) :].strip()
            return remainder or None
    return None


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


def entry_head_key(lemma: str) -> str:
    if lemma.startswith(NOUN_PREFIXES):
        body = lemma[4:]
        if " " not in body:
            return lemma
        noun, _marker = body.rsplit(" ", 1)
        return lemma[:4] + noun
    if lemma.startswith("v "):
        body = lemma[2:]
        first = VERB_SPLIT_RE.split(body, maxsplit=1)[0]
        infinitive = first.split("-", 1)[0]
        return f"v {infinitive}"
    if lemma.startswith("a "):
        return f"a {lemma[2:].split(' ', 1)[0]}"
    return lemma


def extract_verb_infinitive(lemma: str) -> str:
    body = lemma[2:]
    first = VERB_SPLIT_RE.split(body, maxsplit=1)[0]
    return first.split("-", 1)[0]


def extract_verb_auxiliary(lemma: str) -> str:
    body = lemma[2:]
    fields = VERB_SPLIT_RE.split(body)
    if len(fields) < 3:
        return ""
    third = fields[2].strip()
    if third.startswith("hat "):
        return "hat"
    if third == "hat":
        return "hat"
    if third.startswith("ist "):
        return "ist"
    if third == "ist":
        return "ist"
    return ""


def build_duplicate_signature(lemma: str, grammar: str) -> tuple[str, ...]:
    if lemma.startswith(NOUN_PREFIXES):
        body = lemma[4:]
        noun, marker = body.rsplit(" ", 1)
        return ("noun", marker, grammar)
    if lemma.startswith("v "):
        infinitive = extract_verb_infinitive(lemma)
        reflexive = "reflexive" if infinitive.startswith("sich ") else "plain"
        auxiliary = extract_verb_auxiliary(lemma)
        return ("verb", reflexive, auxiliary, grammar)
    if lemma.startswith("a "):
        body = lemma[2:]
        parts = body.split()
        if len(parts) == 1:
            return ("adj", "", "", grammar)
        if len(parts) == 2 and parts[1] == "(indecl.)":
            return ("adj", "(indecl.)", "", grammar)
        if len(parts) >= 3:
            return ("adj", parts[1], " ".join(parts[2:]), grammar)
        return ("adj", body, "", grammar)
    return ("phrase", lemma, grammar)


def duplicate_scope_key(path: Path) -> str:
    language_like = {"ar", "en", "ru", "tr"}
    if path.parent.name in language_like:
        return path.parent.name
    if path.suffix == ".txt" and path.stem in language_like:
        return path.stem
    return str(path.parent)


def is_allowed_duplicate_pair(first: DuplicateEntryRecord, current: DuplicateEntryRecord) -> bool:
    return first.head == "v wiegen" and {
        first.lemma,
        current.lemma,
    } == {
        "v wiegen / wog / hat gewogen",
        "v wiegen / - / hat",
    }


def collect_entry_records(path: Path) -> list[DuplicateEntryRecord]:
    lines, errors = read_lines(path)
    if lines is None or errors:
        return []

    records: list[DuplicateEntryRecord] = []
    index = 0
    total = len(lines)
    while index < total:
        stripped = lines[index].strip()
        line_no = index + 1
        if stripped == "":
            index += 1
            continue

        lemma = stripped
        index += 1

        if index < total:
            index += 1

        grammar = ""
        if index < total:
            grammar_line = lines[index].strip()
            if grammar_line != "" and GRAMMAR_LINE_RE.match(grammar_line):
                grammar = grammar_line
                index += 1

        records.append(
            DuplicateEntryRecord(
                path=path,
                line=line_no,
                head=entry_head_key(lemma),
                signature=build_duplicate_signature(lemma, grammar),
                lemma=lemma,
            )
        )

        while index < total and lines[index].strip() != "":
            index += 1

        while index < total and lines[index].strip() == "":
            index += 1

    return records


def validate_duplicate_heads(paths: Iterable[Path]) -> list[ValidationError]:
    warnings: list[ValidationError] = []
    first_seen: dict[tuple[str, str, tuple[str, ...]], DuplicateEntryRecord] = {}

    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        scope = duplicate_scope_key(path)
        for record in collect_entry_records(path):
            key = (scope, record.head, record.signature)
            if key not in first_seen:
                first_seen[key] = record
                continue
            first_record = first_seen[key]
            if is_allowed_duplicate_pair(first_record, record):
                continue
            warnings.append(
                ValidationError(
                    record.path,
                    record.line,
                    f"duplicate head {record.head!r}; first seen at {first_record.path}:{first_record.line}",
                    severity="warning",
                )
            )

    return warnings


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
                        "translation `prs=` cue must contain a single third-person finite form, not multiple forms",
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
    all_messages: list[ValidationError] = []
    validated_files = 0
    file_paths = list(iter_files(args.paths))

    for path in file_paths:
        file_messages = validate_file(path)
        all_messages.extend(file_messages)
        if path.exists() and path.is_file():
            validated_files += 1

    all_messages.extend(validate_duplicate_heads(file_paths))

    error_count = sum(1 for message in all_messages if message.severity == "error")
    warning_count = sum(1 for message in all_messages if message.severity == "warning")

    if all_messages:
        for message in all_messages:
            stream = sys.stderr if message.severity == "error" else sys.stdout
            print(message.render(), file=stream)

    if error_count:
        summary = f"{error_count} error(s)"
        if warning_count:
            summary += f", {warning_count} warning(s)"
        print(f"{summary} found across {validated_files} file(s).", file=sys.stderr)
        return 1

    if warning_count:
        print(f"Validated {validated_files} file(s); {warning_count} warning(s) found.")
        return 0

    print(f"Validated {validated_files} file(s); no format errors found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
