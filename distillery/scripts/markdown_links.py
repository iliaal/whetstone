"""Validate local Markdown links using CommonMark parsing and GitHub anchors."""

import argparse
import re
import sys
import unicodedata
from functools import lru_cache
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

REPO_ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def _parser():
    try:
        from markdown_it import MarkdownIt
    except ImportError as exc:
        raise SystemExit(
            "Markdown link validation requires markdown-it-py. "
            "Install distillery/requirements.txt before running validation."
        ) from exc
    return MarkdownIt("commonmark").enable(["table", "strikethrough"])


def link_targets(text):
    def visit(tokens):
        for token in tokens:
            if token.type == "link_open":
                yield token.attrGet("href")
            elif token.type == "image":
                yield token.attrGet("src")
            if token.children:
                yield from visit(token.children)

    yield from visit(_parser().parse(_without_frontmatter(text)))


def _without_frontmatter(text):
    return re.sub(r"\A---\r?\n.*?\r?\n(?:---|\.\.\.)[ \t]*(?:\r?\n|$)", "", text, count=1, flags=re.S)


def _heading_slug(text):
    # Keep literal underscores and repeated spaces; only Markdown formatting disappears.
    return "".join(
        char for char in text.lower()
        if char in " -" or unicodedata.category(char) in {
            "Lu", "Ll", "Lt", "Lm", "Lo", "Mn", "Mc", "Me", "Nd", "Nl", "Pc"
        }
    ).replace(" ", "-")


class _Anchors(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.anchors = set()
        self.heading_slugs = set()
        self.heading = None
        self.heading_text = []
        self.code_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"pre", "code"}:
            self.code_depth += 1
        if tag == "a" and not self.code_depth:
            self.anchors.update(value for key, value in attrs if key in {"id", "name"} and value)
        if re.fullmatch(r"h[1-6]", tag) and not self.code_depth:
            self.heading = tag
            self.heading_text = []

    def handle_endtag(self, tag):
        if tag == self.heading:
            original = _heading_slug("".join(self.heading_text))
            slug = original
            suffix = 0
            while slug in self.heading_slugs:
                suffix += 1
                slug = f"{original}-{suffix}"
            self.heading_slugs.add(slug)
            self.anchors.add(slug)
            self.heading = None
        if tag in {"pre", "code"}:
            self.code_depth = max(0, self.code_depth - 1)

    def handle_data(self, data):
        if self.heading:
            self.heading_text.append(data)


def markdown_anchors(text):
    parser = _Anchors()
    parser.feed(_parser().render(_without_frontmatter(text)))
    parser.close()
    return parser.anchors


def broken_local_links(text, base_dir, anchor_cache=None, repo_root=None):
    """Return (target, reason) pairs; fragments are checked only on Markdown files."""
    cache = anchor_cache if anchor_cache is not None else {}
    repo_root = repo_root or REPO_ROOT
    broken = []
    for target in link_targets(text):
        parts = urlsplit(target)
        if parts.scheme or parts.netloc:
            continue
        path = unquote(parts.path)
        fragment = unquote(parts.fragment)
        if not path:
            if fragment and fragment not in markdown_anchors(text):
                broken.append((target, "missing fragment"))
            continue
        if "." not in Path(path).name and "/" not in path:
            continue
        resolved = (repo_root / path.lstrip("/") if path.startswith("/") else base_dir / path).resolve()
        markdown = resolved.suffix.lower() in {".md", ".markdown", ".mdown", ".mkdn"}
        resource = path.startswith(("./references/", "./scripts/"))
        if not resolved.exists() or ((markdown or resource) and not resolved.is_file()):
            broken.append((target, "missing file"))
        elif fragment and markdown:
            if resolved not in cache:
                cache[resolved] = markdown_anchors(resolved.read_text(encoding="utf-8"))
            if fragment not in cache[resolved]:
                broken.append((target, "missing fragment"))
    return list(dict.fromkeys(broken))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("paths", type=Path, nargs="+")
    args = parser.parse_args()
    files = set()
    for path in args.paths:
        if not path.exists():
            parser.error(f"path does not exist: {path}")
        files.update(path.rglob("*.md") if path.is_dir() else [path])
    if not files:
        parser.error("no Markdown files found in the requested paths")
    cache = {}
    errors = 0
    for path in sorted(files):
        for target, reason in broken_local_links(path.read_text(encoding="utf-8"), path.parent, cache, args.repo_root):
            print(f"  ERROR: {path} links to {reason}: {target}")
            errors += 1
    return int(errors > 0)


if __name__ == "__main__":
    sys.exit(main())
