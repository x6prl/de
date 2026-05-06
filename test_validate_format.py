from pathlib import Path
import tempfile
import unittest

import validate_format


TEST_PATH = Path("test.txt")


class ValidateVerbRegularityTest(unittest.TestCase):
    def validate(self, lemma: str) -> list[str]:
        return [error.message for error in validate_format.validate_lemma(TEST_PATH, 1, lemma)]

    def test_regular_verb_with_omitted_default_forms_is_valid(self) -> None:
        self.assertEqual(self.validate("v wandern / - / ist"), [])

    def test_regular_verb_with_explicit_regular_forms_is_invalid(self) -> None:
        self.assertEqual(
            self.validate("v wandern / wanderte / ist gewandert"),
            [
                "verb Prateritum field stores only regular forms; use `-` instead",
                "verb auxiliary/participle field stores a regular participle; keep only the auxiliary",
            ],
        )

    def test_regular_present_exception_is_invalid(self) -> None:
        self.assertEqual(
            self.validate("v machen-macht"),
            ["verb present-tense exception stores only regular forms; omit the exception block"],
        )

    def test_separable_reflexive_regular_forms_are_invalid(self) -> None:
        self.assertEqual(
            self.validate("v sich ausruhen-ruht sich aus / ruhte sich aus / hat sich ausgeruht"),
            [
                "verb present-tense exception stores only regular forms; omit the exception block",
                "verb Prateritum field stores only regular forms; use `-` instead",
                "verb auxiliary/participle field stores a regular participle; keep only the auxiliary",
            ],
        )

    def test_mixed_regular_and_irregular_variant_is_allowed(self) -> None:
        self.assertEqual(self.validate("v backen-backt,bäckt / backte,buk / hat gebacken"), [])


class DuplicateHeadValidationTest(unittest.TestCase):
    def test_duplicate_head_is_scoped_per_language_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            en = root / "en"
            ru = root / "ru"
            en.mkdir()
            ru.mkdir()
            (en / "a.txt").write_text("v wandern\nwalk;\n", encoding="utf-8")
            (en / "b.txt").write_text("v wandern / - / ist\nhike;\n", encoding="utf-8")
            (ru / "a.txt").write_text("v wandern\nгулять;\n", encoding="utf-8")

            warnings = validate_format.validate_duplicate_heads([en / "a.txt", en / "b.txt", ru / "a.txt"])

            self.assertEqual(len(warnings), 1)
            self.assertEqual(warnings[0].severity, "warning")
            self.assertIn("duplicate head 'v wandern'", warnings[0].message)
            self.assertEqual(warnings[0].path, en / "b.txt")

    def test_duplicate_head_key_normalizes_verb_forms(self) -> None:
        self.assertEqual(
            validate_format.entry_head_key("v sich ausruhen-ruht sich aus / ruhte sich aus / hat sich ausgeruht"),
            "v sich ausruhen",
        )


if __name__ == "__main__":
    unittest.main()
