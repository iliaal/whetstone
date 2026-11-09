"""Regression tests for the trigger-overlap CLI (no optional dependencies)."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("check-trigger-overlap.py")
PATTERNS = """SKILL_PATTERNS[alpha]='shared common alpha'
SKILL_PATTERNS[beta]='shared common alpha'
SKILL_PATTERNS[gamma]='shared gamma'
SKILL_TIERS[alpha]=1
SKILL_TIERS[beta]=1
SKILL_TIERS[gamma]=2
"""


class TriggerOverlapTests(unittest.TestCase):
    def run_report(self, *args, patterns=PATTERNS):
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / "patterns.sh"
            fixture.write_text(patterns, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(SCRIPT), "--patterns", str(fixture), *args],
                capture_output=True, text=True, check=False,
            )

    def test_strict_detects_matches_outside_display_limit(self):
        for top in (0, 1, 2, 3, 4):
            with self.subTest(top=top):
                result = self.run_report("--strict", "--top", str(top))
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("2 cross-tier pair(s) at/above threshold out of 3 total.", result.stdout)
                self.assertEqual(result.stdout.count(" <-> "), min(top, 3))

    def test_negative_display_limits_are_argument_errors(self):
        for strict in (False, True):
            for top in (-1, -3, -1000000):
                for threshold in ("0.1", "1.1"):
                    with self.subTest(strict=strict, top=top, threshold=threshold):
                        args = ["--top", str(top), "--threshold", threshold]
                        if strict:
                            args.append("--strict")
                        result = self.run_report(*args)
                        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                        self.assertEqual(result.stdout, "")
                        self.assertIn("error: --top must be non-negative", result.stderr)

    def test_advisory_reports_all_matches_without_failing(self):
        result = self.run_report("--top", "1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("2 cross-tier pair(s) at/above threshold out of 3 total.", result.stdout)
        self.assertEqual(result.stdout.count(" <-> "), 1)

    def test_strict_accepts_same_tier_only_matches(self):
        result = self.run_report("--strict", "--threshold", "0.5", "--top", "0")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("0 cross-tier pair(s) at/above threshold out of 1 total.", result.stdout)

    def test_cross_tier_threshold_is_inclusive(self):
        for threshold, expected_status, expected_count in ((0.249, 1, 2), (0.25, 1, 2), (0.251, 0, 0)):
            with self.subTest(threshold=threshold):
                result = self.run_report("--strict", "--threshold", str(threshold), "--top", "0")
                self.assertEqual(result.returncode, expected_status, result.stdout + result.stderr)
                self.assertIn(f"{expected_count} cross-tier pair(s) at/above threshold", result.stdout)

    def test_nonfinite_thresholds_are_argument_errors(self):
        for strict in (False, True):
            for threshold in ("nan", "NaN", "+nan", "-nan", "inf", "+inf", "-inf",
                              "Infinity", "-Infinity", "1e309", "-1e309"):
                with self.subTest(strict=strict, threshold=threshold):
                    args = [f"--threshold={threshold}"]
                    if strict:
                        args.append("--strict")
                    result = self.run_report(*args)
                    self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                    self.assertEqual(result.stdout, "")
                    self.assertIn("error: --threshold must be finite", result.stderr)

    def test_finite_extremes_keep_existing_threshold_semantics(self):
        for threshold, status, matches in (("-1e308", 1, True), ("0", 1, True),
                                           ("1", 0, True), ("1.1", 0, False),
                                           ("1e308", 0, False)):
            with self.subTest(threshold=threshold):
                result = self.run_report("--strict", f"--threshold={threshold}", "--top", "0")
                self.assertEqual(result.returncode, status, result.stdout + result.stderr)
                self.assertEqual(result.stderr, "")
                self.assertEqual("No skill pairs" not in result.stdout, matches)

    def test_strict_accepts_no_matches(self):
        result = self.run_report("--strict", "--threshold", "1.1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("No skill pairs", result.stdout)

    def test_regex_escapes_do_not_prefix_trigger_words(self):
        for pattern in (r"\breview\b \bcode\b", r"review\scode",
                        r"review\Scode", r"review\wcode", r"review\Wcode",
                        r"\Breview\Bcode", r"\bthe\b \breview\b \bcode\b"):
            with self.subTest(pattern=pattern):
                patterns = (f"SKILL_PATTERNS[alpha]='{pattern}'\n"
                            "SKILL_PATTERNS[beta]='review code'\n")
                result = self.run_report("--strict", "--threshold", "1", patterns=patterns)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("1.00 [CROSS-TIER]  alpha <-> beta", result.stdout)
                self.assertIn("shared: code, review", result.stdout)

    def test_escaped_backslash_preserves_following_literal_word(self):
        for word, expected_status in (("breview", 1), ("review", 0)):
            with self.subTest(word=word):
                patterns = (r"SKILL_PATTERNS[alpha]='\\breview'" + "\n"
                            f"SKILL_PATTERNS[beta]='{word}'\n")
                result = self.run_report("--strict", "--threshold", "1", patterns=patterns)
                self.assertEqual(result.returncode, expected_status, result.stdout + result.stderr)
                if expected_status:
                    self.assertIn("shared: breview", result.stdout)

    def test_escaped_punctuation_keeps_neighboring_trigger_words(self):
        patterns = (r"SKILL_PATTERNS[alpha]='review\.code\+patch'" + "\n"
                    "SKILL_PATTERNS[beta]='review code patch'\n")
        result = self.run_report("--strict", "--threshold", "1", patterns=patterns)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("shared: code, patch, review", result.stdout)


if __name__ == "__main__":
    unittest.main()
