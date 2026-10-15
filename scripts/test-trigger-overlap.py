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

    def test_strict_accepts_no_matches(self):
        result = self.run_report("--strict", "--threshold", "1.1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("No skill pairs", result.stdout)


if __name__ == "__main__":
    unittest.main()
