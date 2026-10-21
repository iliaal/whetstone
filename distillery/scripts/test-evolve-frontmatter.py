#!/usr/bin/env python3
"""Offline regression checks: python3 distillery/scripts/test-evolve-frontmatter.py."""

import unittest

from evolve import _reassemble_skill, _split_skill


class EvolveFrontmatterTests(unittest.TestCase):
    def test_inline_separators_keep_entire_header_out_of_body(self):
        for newline in ("\n", "\r\n"):
            for description in (
                "Compare input --- and output.",
                '"Compare input --- and output."',
                ">-\n  Compare input --- and output.",
            ):
                with self.subTest(newline=newline, description=description):
                    header = (
                        "---\nname: ia-example\ndescription: " + description
                        + "\nclass: discipline\n---"
                    ).replace("\n", newline)
                    body = "# Procedure\n\nKeep input --- output.\n\n---\n\nEnd.\n".replace("\n", newline)
                    self.assertEqual(_split_skill(header + newline * 2 + body), (header, body))

    def test_reassembly_preserves_metadata_when_body_changes(self):
        header = '---\nname: ia-example\ndescription: "Compare --- values."\nclass: discipline\n---'
        frontmatter, body = _split_skill(header + "\n\nOld instructions.\n")
        self.assertEqual(body, "Old instructions.\n")
        self.assertEqual(_reassemble_skill(frontmatter, "New instructions."),
                         header + "\n\nNew instructions.\n")

    def test_non_delimiter_lines_leave_input_untouched(self):
        for text in (
            "# Preamble\n---\nname: ia-example\n---\nBody",
            "---prefix\nname: ia-example\n---\nBody",
            "---\nname: ia-example\n---suffix\nBody",
            "---\nname: ia-example\n ---\nBody",
            "---\nname: ia-example\nBody",
            "---",
            "",
        ):
            with self.subTest(text=text):
                self.assertEqual(_split_skill(text), ("", text))

    def test_delimiters_at_eof_and_with_trailing_whitespace(self):
        for newline in ("\n", "\r\n"):
            for padding in ("", " \t"):
                header = f"---{padding}{newline}name: ia-example{newline}---{padding}"
                with self.subTest(newline=newline, padding=padding):
                    self.assertEqual(_split_skill(header), (header, ""))
                    self.assertEqual(_split_skill(header + newline * 2 + "  Indented body\n"),
                                     (header, "  Indented body\n"))


if __name__ == "__main__":
    unittest.main()
