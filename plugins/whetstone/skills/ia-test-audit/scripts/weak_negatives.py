#!/usr/bin/env python3
"""Flag negative tests whose assertion cannot tell which guard refused.

Each hit is a candidate for Ineffective for the claim (a test that may pass without
reaching the guard it names). Confirm hits with a reach probe or a mutation check before acting on them.

Kinds:
  status-only      asserts a nonzero exit code or 4xx/5xx status and nothing that names
                   the refusal (message, error type plus message, validation key, body)
  or-alternative   accepts either of two messages, so the earlier guard satisfies it
  bare-throw       expects a generic exception type (or any error, in JS) with no message
                   or matcher, and nothing else in the test names the refusal
  should-panic     Rust #[should_panic] with no expected = "..."

Languages by extension: .py (AST), .rs, .php (PHPUnit and Pest), .js/.jsx/.ts/.tsx/.mjs/.cjs/.mts/.cts.
"""

from __future__ import annotations

import argparse
import ast
import glob
import re
import sys
from collections import Counter
from pathlib import Path

SKIP_DIRS = {
    "node_modules",
    "vendor",
    ".git",
    "target",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
    "coverage",
    ".claude",
    ".next",
    ".turbo",
    ".worktrees",
}


def expand(patterns: list[str]) -> list[str]:
    """Glob, dropping dependency, build, and agent-worktree directories."""
    found = {f for p in patterns for f in glob.glob(p, recursive=True)}
    return sorted(f for f in found if Path(f).is_file() and not SKIP_DIRS.intersection(Path(f).parts))


Hit = tuple[str, int, str, str, str]

GENERIC_ERRORS = {
    "Exception",
    "BaseException",
    "RuntimeException",
    "RuntimeError",
    "InvalidArgumentException",
    "LogicException",
    "ValueError",
    "TypeError",
    "KeyError",
    "AssertionError",
    "OSError",
    "SystemExit",
    "CalledProcessError",
    "ValidationException",
    "HttpException",
    "AuthorizationException",
    "AuthenticationException",
    "QueryException",
    "Throwable",
    "Error",
    "ErrorException",
    "UnexpectedValueException",
    "DomainException",
}
PY_STATUS_ATTRS = {"returncode", "status_code", "exit_code", "status", "rc", "code"}
PY_DETAIL_WORDS = re.compile(
    r"stderr|stdout|message|output|match|excinfo|body|error|detail|reason", re.IGNORECASE
)
PY_CHECKER_CALL = re.compile(r"assert|expect|refus|reject|deny|denied|fail", re.IGNORECASE)


def _is_nonzero_int(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, int)
        and not isinstance(node.value, bool)
        and node.value != 0
    )


def _status_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Attribute) and node.attr in PY_STATUS_ATTRS:
        return node.attr
    if isinstance(node, ast.Name) and node.id in PY_STATUS_ATTRS:
        return node.id
    return None


HTTP_STATUS_ATTRS = {"status_code", "status"}
SUCCESS_NAME = re.compile(r"(?:^|_)(?:OK|SUCCESS|PASS|CLEAN|ZERO)(?:_|$)")


def _is_refusal_value(attr: str, node: ast.AST) -> bool:
    if attr in HTTP_STATUS_ATTRS:
        return isinstance(node, ast.Constant) and isinstance(node.value, int) and 400 <= node.value <= 599
    if isinstance(node, ast.Name | ast.Attribute):
        name = ast.unparse(node).split(".")[-1]
        return name.isupper() and not SUCCESS_NAME.search(name)
    return _is_nonzero_int(node)


def _is_zero(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and node.value == 0


def _is_exit_name(node: ast.AST) -> bool:
    return _status_name(node) not in (None, *HTTP_STATUS_ATTRS)


def _py_status_assert(test: ast.AST) -> bool:
    if not isinstance(test, ast.Compare) or len(test.ops) != 1:
        return False
    left, right, op = test.left, test.comparators[0], test.ops[0]
    if isinstance(op, ast.Eq):
        if (attr := _status_name(left)) is not None and _is_refusal_value(attr, right):
            return True
        return (attr := _status_name(right)) is not None and _is_refusal_value(attr, left)
    if isinstance(op, ast.NotEq):
        return (_is_exit_name(left) and _is_zero(right)) or (_is_exit_name(right) and _is_zero(left))
    return False


def _py_detail_checked(func: ast.AST) -> bool:
    for node in ast.walk(func):
        if isinstance(node, ast.Assert) and not _py_status_assert(node.test):
            test = node.test
            membership = isinstance(test, ast.Compare) and any(
                isinstance(o, ast.In | ast.NotIn) for o in test.ops
            )
            if PY_DETAIL_WORDS.search(ast.unparse(test)) or (
                membership and _status_name(test.left) is None and not _is_nonzero_int(test.left)
            ):
                return True
        if isinstance(node, ast.Call):
            name = ast.unparse(node.func)
            if "raises" in name and any(k.arg == "match" for k in node.keywords):
                return True
            if PY_CHECKER_CALL.search(name) and any(
                isinstance(n, ast.Constant) and isinstance(n.value, str | bytes) and len(n.value) >= 6
                for arg in [*node.args, *(k.value for k in node.keywords)]
                for n in ast.walk(arg)
            ):
                return True
    return False


def scan_python(path: str, text: str) -> list[Hit]:
    tree = ast.parse(text)
    hits: list[Hit] = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef | ast.AsyncFunctionDef) or not func.name.startswith("test"):
            continue
        status_line = None
        for node in ast.walk(func):
            if isinstance(node, ast.Assert):
                if _py_status_assert(node.test) and status_line is None:
                    status_line = node.lineno
                t = node.test
                if isinstance(t, ast.BoolOp) and isinstance(t.op, ast.Or):
                    ins = [
                        v
                        for v in t.values
                        if isinstance(v, ast.Compare) and any(isinstance(o, ast.In) for o in v.ops)
                    ]
                    if len(ins) >= 2:
                        hits.append((path, node.lineno, "or-alternative", func.name, ast.unparse(t)[:140]))
            if isinstance(node, ast.With | ast.AsyncWith):
                for item in node.items:
                    call = item.context_expr
                    if (
                        isinstance(call, ast.Call)
                        and ast.unparse(call.func).endswith("raises")
                        and not any(k.arg == "match" for k in call.keywords)
                        and call.args
                        and ast.unparse(call.args[0]).split(".")[-1] in GENERIC_ERRORS
                    ):
                        var = item.optional_vars
                        used = var is not None and any(
                            isinstance(n, ast.Name) and n.id == ast.unparse(var) and n is not var
                            for stmt in func.body
                            for n in ast.walk(stmt)
                            if stmt is not node
                        )
                        if not used:
                            hits.append((path, node.lineno, "bare-throw", func.name, ast.unparse(call)[:140]))
        if status_line is not None and not _py_detail_checked(func):
            hits.append(
                (path, status_line, "status-only", func.name, "status/exit code is the only refusal evidence")
            )
    return hits


def _blocks(text: str, start_re: re.Pattern[str]) -> list[tuple[int, str, str]]:
    starts = [(m.start(), m.group("name")) for m in start_re.finditer(text)]
    out = []
    for i, (offset, name) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(text)
        out.append((text.count("\n", 0, offset) + 1, name, text[offset:end]))
    return out


JS_START = re.compile(r"\b(?:it|test)(?:\.(?:only|each\([^)]*\)|concurrent))?\s*\(\s*(['\"`])(?P<name>.+?)\1")
JS_BARE_THROW = re.compile(r"\.(?:toThrow|toThrowError)\(\s*\)")
JS_STATUS = re.compile(
    r"expect\([^)]*\.(?:status|statusCode|exitCode|code)\)\s*\.(?:toBe|toEqual|toStrictEqual)\(\s*(?:[45]\d\d|[1-9]\d?)\s*\)"
    r"|toHaveProperty\(\s*['\"](?:status|statusCode)['\"]\s*,\s*[45]\d\d"
    r"|\.expect\(\s*[45]\d\d\s*\)(?!\s*\.\s*expect)"
    r"|toHaveStatus\(\s*[45]\d\d"
)
JS_DETAIL = re.compile(
    r"expect\([^)]*(?:body|message|error|text|json|data|detail|stderr|stdout|errors)\b"
    r"|\.(?:toThrow|toThrowError|rejects\.toThrow)\(\s*[^\s)]"
    r"|toMatchObject|toMatchInlineSnapshot|toMatchSnapshot|toContain\(|toMatch\("
    r"|toHaveBeenCalledWith\([^)]*['\"`]"
)
JS_OR = re.compile(r"expect\([^;]*\|\|[^;]*\)\s*\.(?:toBe\(\s*true|toBeTruthy)")


def scan_js(path: str, text: str) -> list[Hit]:
    hits: list[Hit] = []
    for line, name, body in _blocks(text, JS_START):
        if (m := JS_BARE_THROW.search(body)) and not JS_DETAIL.search(body):
            hits.append((path, line, "bare-throw", name, m.group(0)))
        if JS_STATUS.search(body) and not JS_DETAIL.search(body):
            hits.append((path, line, "status-only", name, JS_STATUS.search(body).group(0)[:140]))
        if m := JS_OR.search(body):
            hits.append((path, line, "or-alternative", name, m.group(0)[:140]))
    return hits


PHP_START = re.compile(
    r"function\s+(?P<name>test\w*)\s*\("
    r"|(?:#\[Test\]|@test)[\s\S]{0,200}?function\s+(?P<name2>\w+)\s*\("
    r"|^\s*(?:it|test)\s*\(\s*(['\"])(?P<name3>.+?)\3",
    re.MULTILINE,
)
PHP_STATUS = re.compile(
    r"->assert(?:Status\(\s*[45]\d\d|Forbidden|Unauthorized|NotFound|Unprocessable|BadRequest|Conflict|ServerError|MethodNotAllowed)\b"
)
PHP_DETAIL = re.compile(
    r"assertJsonValidationErrors|assertInvalid|assertJsonPath|assertJsonFragment|assertJson\(|assertExactJson|assertSee"
    r"|assertSessionHasErrors|expectExceptionMessage|assertStringContainsString|assertJsonStructure|->json\(\s*['\"]"
)
PHP_EXPECT = re.compile(r"expectException\(\s*(?P<cls>[\w\\]+)::class")


def scan_php(path: str, text: str) -> list[Hit]:
    hits: list[Hit] = []
    starts = []
    for m in PHP_START.finditer(text):
        starts.append((m.start(), m.group("name") or m.group("name2") or m.group("name3")))
    for i, (offset, name) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(text)
        body, line = text[offset:end], text.count("\n", 0, offset) + 1
        if (m := PHP_STATUS.search(body)) and not PHP_DETAIL.search(body):
            hits.append((path, line, "status-only", name, m.group(0)))
        for m in PHP_EXPECT.finditer(body):
            if "expectExceptionMessage" not in body and m.group("cls").split("\\")[-1] in GENERIC_ERRORS:
                hits.append(
                    (path, line, "bare-throw", name, f"expectException({m.group('cls')}) without a message")
                )
                break
        for m in re.finditer(r"->(?:throws|toThrow)\(\s*(?P<cls>[\w\\]+)::class\s*\)", body):
            if m.group("cls").split("\\")[-1] in GENERIC_ERRORS:
                hits.append(
                    (path, line, "bare-throw", name, f"Pest throws({m.group('cls')}) without a message")
                )
                break
    return hits


RS_START = re.compile(r"#\[test\](?P<attrs>(?:\s*#\[[^\]]*\])*)\s*(?:async\s+)?fn\s+(?P<name>\w+)")
RS_IS_ERR = re.compile(r"assert!\(\s*[^;]*?\.is_err\(\)\s*\)|matches!\([^;]*Err\(\s*_\s*\)\s*\)")
RS_DETAIL = re.compile(
    r"unwrap_err\(\)|\.err\(\)|to_string\(\)|expect_err|Err\(\s*[A-Z]\w*(?:::\w+)+|contains\("
)


def scan_rust(path: str, text: str) -> list[Hit]:
    hits: list[Hit] = []
    starts = [(m.start(), m.group("name"), m.group("attrs")) for m in RS_START.finditer(text)]
    for i, (offset, name, attrs) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(text)
        body, line = text[offset:end], text.count("\n", 0, offset) + 1
        leading = []
        for prior in reversed(text[:offset].splitlines()):
            if not prior.strip().startswith(("#[", "///")):
                break
            leading.append(prior)
        if "#[should_panic]" in attrs or any("#[should_panic]" in p for p in leading):
            hits.append((path, line, "should-panic", name, "#[should_panic] without expected ="))
        if (m := RS_IS_ERR.search(body)) and not RS_DETAIL.search(body):
            hits.append((path, line, "status-only", name, m.group(0)[:140]))
    return hits


SCANNERS = {
    ".py": scan_python,
    ".rs": scan_rust,
    ".php": scan_php,
    **{ext: scan_js for ext in (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".mts", ".cts")},
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("patterns", nargs="+", help="globs of test files (** allowed)")
    parser.add_argument("--kind", action="append", help="only report these kinds")
    args = parser.parse_args()

    pattern_files = [(pattern, expand([pattern])) for pattern in args.patterns]
    matched = sorted({name for _, names in pattern_files for name in names})
    unmatched = [pattern for pattern, names in pattern_files if not names]
    for pattern in unmatched:
        print(f"weak_negatives: unmatched pattern (no eligible files): {pattern}", file=sys.stderr)
    files = [name for name in matched if Path(name).suffix in SCANNERS]
    unsupported = [name for name in matched if Path(name).suffix not in SCANNERS]
    if not files:
        print("weak_negatives: no supported files matched; audit input is incomplete", file=sys.stderr)
        return 2
    for name in unsupported:
        print(f"weak_negatives: unsupported file: {name}", file=sys.stderr)
    hits: list[Hit] = []
    failures = 0
    for name in files:
        scanner = SCANNERS[Path(name).suffix]
        try:
            hits.extend(scanner(name, Path(name).read_text(errors="replace")))
        except (OSError, SyntaxError) as error:
            failures += 1
            print(f"weak_negatives: unparsed {name}: {error}", file=sys.stderr)
    if args.kind:
        hits = [h for h in hits if h[2] in args.kind]
    for path, line, kind, test, detail in sorted(hits):
        print(f"{path}:{line}  [{kind}]  {test}  -- {detail}")
    counts = Counter(h[2] for h in hits)
    summary = ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) or "none"
    print(
        f"\n{len(files) - failures} supported files scanned; {failures} unparsed; "
        f"{len(unsupported)} unsupported; {len(unmatched)} unmatched patterns; "
        f"{len(hits)} candidates ({summary})",
        file=sys.stderr,
    )
    return 2 if failures or unsupported or unmatched else 0


if __name__ == "__main__":
    sys.exit(main())
