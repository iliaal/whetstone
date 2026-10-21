"""Regressions for counting document text containing tokenizer markers."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import tiktoken

import distiller


class TokenCountTests(unittest.TestCase):
    def test_literal_markers_are_ordinary_text(self):
        encoder = tiktoken.get_encoding("cl100k_base")
        for marker in sorted(encoder.special_tokens_set):
            with self.subTest(marker=marker):
                text = f"Document the literal {marker} marker, not a control token."
                expected = len(encoder.encode(text, disallowed_special=()))
                self.assertEqual(distiller.count_tokens(text), expected)
                self.assertGreater(expected, len(encoder.encode(text, allowed_special="all")))

    def test_file_and_cli_count_literal_markers(self):
        text = "Example: <|endoftext|> and <|fim_prefix|>.\n"
        expected = len(tiktoken.get_encoding("cl100k_base").encode(text, disallowed_special=()))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "SKILL.md"
            path.write_text(text, encoding="utf-8")
            self.assertEqual(distiller.token_count(path), expected)
            result = subprocess.run(
                [sys.executable, str(Path(distiller.__file__)), "token-count", str(path)],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(int(result.stdout.strip()), expected)

    def test_budget_counts_body_and_references(self):
        encoder = tiktoken.get_encoding("cl100k_base")
        body = "Explain <|fim_middle|> literally."
        reference = "Example <|fim_suffix|>."
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "SKILL.md").write_text(body, encoding="utf-8")
            (root / "references").mkdir()
            (root / "references" / "example.md").write_text(reference, encoding="utf-8")
            report = distiller.token_budget_report(root)
            self.assertEqual(report["body_tokens"], len(encoder.encode(body, disallowed_special=())))
            self.assertEqual(report["total_tokens"],
                             len(encoder.encode(body, disallowed_special=())) + len(encoder.encode(reference, disallowed_special=())))


if __name__ == "__main__":
    unittest.main()
