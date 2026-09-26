#!/usr/bin/env python3
"""Flag likely redundant tests by structure: same action, same or nested assertions, same shape.

Each test is reduced to an action signature (the statements that build input and exercise
the code, in order) and an assertion set. Groups are candidates, not verdicts: two tests
with one signature can still guard different contracts through state the detector cannot
see (a helper's computed default, a fixture's state, an environment variable). Pairs are
formed within one file unless --cross-file is given, because identical text in two files
usually exercises two modules (a per-file import, constant, fixture, or setUp).

Kinds:
  REDUNDANT    same action, identical assertion sets: one of the tests adds nothing.
  SUBSUMED     same action, one assertion set a strict subset of another. The subsumer
               keeps; the first-listed (subsumed) test is the candidate.
  FOLD         same action, different assertion sets: one input, several observables.
               Fold into one test that asserts all of them.
  PARAMETRIZE  one table-driven test could replace the group. Match `shape`: identical
               structure once every literal is abstracted; the same action shape where one
               test adds one assertion shape, or replaces one with another on the same
               subject; or identical result assertions (at least one beyond an exit or
               status code) over setups at least --ratio similar with the same final act,
               whose differing statements call the same callee or act on the same object,
               plus at most one statement only one test runs. Match `kwarg-superset`:
               identical calls and identical or nested assertions, but one test also passes
               keyword arguments; that is a separate table row, or a duplicate when those
               values are the callee's defaults (the reason names them).

When full assertion sets are unrelated but the assertions after the act are equal or
nested, REDUNDANT/SUBSUMED is still reported and the reason names the precondition asserts
(fixture checks before the act) that were set aside.

Gates on FOLD and PARAMETRIZE (every pair in a group must pass; no transitive chaining):
  - The expected status is an observable: exit codes and success/refusal polarity (`== 0`,
    `!= 0`, `is_err`, `assertStatus(422)`, `pytest.raises`) must match. PARAMETRIZE may add
    a row with another status only to a parametrized family whose cases already differ in
    status. FOLD refuses two different expected statuses.
  - PARAMETRIZE refuses assertion shapes that differ only in polarity or strength (`in` /
    `not in`, `==` / `!=`, `contains` / `!contains` / `starts_with`, `is_some` / `is_none`),
    and never pairs cases of two different parametrized families.
  - Harness: a statement shape found in more than half of a file's tests is harness. With no
    shared distinguishing literal (IDF-weighted literal lines of eight characters or more,
    excluding literals that only select what to read, such as `text.index("## Phase 3")`),
    at least 70% of the pair's statements must be non-harness.
  - Observation-only tests (Python: no call that feeds a literal or acts on an object, such
    as a document read and sliced) pair only when their needles overlap: a distinguishing
    shared needle covering at least half of the smaller needle set.
Groups are cliques of qualifying pairs, strongest first, at most six members; overflow is
named in the reason. `score` ranks PARAMETRIZE groups within a file by shared literal
weight: identical distinguishing inputs across differently named tests rank first.

Python (ast):
  - Tests are module-level and class-level `test*` functions. Fixture parameters are part
    of the signature (scoped to the file that defines them, else to its directory), as are
    `usefixtures` marks.
  - `pytest.mark.parametrize` expands into cases (at most 64): argument names are replaced
    by each case's values and `if`/ternary tests that become constant are folded, so a
    plain test can match one case. Cases of one function are siblings and never paired.
    Non-literal argvalues stay symbolic parameters.
  - Module-level constants bound to literals are substituted, so `approvals=NAMED` and the
    same dict literal compare equal. A keyword equal to a same-module helper's default is
    dropped; defaults come from the signature, or from a literal dict the helper merges
    `**kwargs` over (keys the helper assigns again are computed, so unknown). Helpers and
    constants imported from other modules are not resolved.
  - Normalization: assert messages dropped; skip guards (`if ...: pytest.skip()`) dropped;
    single-assignment bindings with no call (`world = fixture`, `p = root / "x"`) inlined;
    observation bindings (values built only from readers such as `json.loads`,
    `read_text`, `exists`) inlined into the assertions that use them, unless an action
    runs between the read and its use (a snapshot stays an action); loops whose body is
    only assertions count as one assertion; remaining locals renamed v0, v1, ... in order
    of first appearance, action statements first.
  - Incidental literals: an integer of two or more digits, or a digit run in a string not
    preceded by a letter or digit, that occurs at least twice in the setup and act (not
    counting assertions) and never as the operand of an exit-code or status comparison, is
    a threaded identifier (a round number, a record id) and becomes ID0, ID1, ... by first
    appearance, everywhere in the test. String path segments joined onto a `tmp*` fixture become TMP0, ....
    All other literals are kept for REDUNDANT/SUBSUMED/FOLD and abstracted for PARAMETRIZE.
  - Assertions: `assert`, calls named `assert*`/`expect*`/`verify*`/`check*` (including
    `self.assertEqual` and mock `assert_called_*`), `pytest.fail`, and `pytest.raises` /
    `pytest.warns` / `assertRaises` context managers. An assertion that exercises code
    (`assert run(...).returncode == 0`, or a non-reader call given a string, bytes, or
    f-string literal input) is also recorded as an action. A call whose only literal
    input is a number (`assert f(10) == 1`) is not, so identical tests built only from
    such assertions are not grouped.

Rust (#[test], #[tokio::test], #[rstest], #[test_case]), PHP (PHPUnit test methods,
#[Test]/@test, Pest it()/test()), JS/TS (it/test blocks, including .each): token-based.
Comments and whitespace are stripped; locals are canonicalized (Rust `let` bindings, PHP
`$variables`, JS `const`/`let`/`var` bindings); statements are split at top-level `;` (and
line breaks in JS). A statement is an assertion when it starts with `assert*!` (Rust),
`$this->assert*`/`self::assert*`/`expect(` (PHP), or `expect(`/`assert` (JS); PHP
`->assert*` and supertest `.expect(` chains are split so the call before them is the action.
An assertion whose argument calls something other than a known query or reader
(`assertTrue($this->policy->view($user))`) is also recorded as an action. Data-driven
tests (PHPUnit data providers and parameters, Pest `->with()`, `it.each` tables, rstest
cases) carry their data source in the signature. Literals are kept for exact kinds and
abstracted for PARAMETRIZE. Limits: no fixture, `beforeEach`/`setUp`, helper-default, or
constant resolution; no case expansion (a dataset or table is one unit); statements are
compared as token strings, so reordered setup or an extracted helper hides a duplicate.
"""

from __future__ import annotations

import argparse
import ast
import difflib
import glob
import itertools
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

if sys.version_info < (3, 11):
    print("duplicate_tests: Python 3.11+ required", file=sys.stderr)
    sys.exit(2)

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


@dataclass
class Unit:
    path: str
    line: int
    func: str
    name: str
    fixtures: tuple[str, ...]
    actions: tuple[str, ...]
    action_pos: tuple[str, ...]
    action_kwargs: tuple[tuple[tuple[str, str], ...], ...]
    pre: frozenset[str]
    post: frozenset[str]
    action_shape: tuple[str, ...]
    assert_shape: tuple[str, ...]
    act_shape: str
    setup_shape: tuple[str, ...] = ()
    params: bool = False
    status: frozenset[str] = frozenset()
    inputs: frozenset[str] = frozenset()
    needles: frozenset[str] = frozenset()
    real_act: bool = True
    notes: list[str] = field(default_factory=list)

    @property
    def shape(self) -> tuple[str, ...]:
        return self.action_shape + self.assert_shape

    @property
    def full(self) -> frozenset[str]:
        return self.pre | self.post

    def ref(self) -> dict[str, object]:
        return {"file": self.path, "line": self.line, "test": self.name}


# ---------------------------------------------------------------- observables shared by every language

STRING_LITERAL = re.compile(r"""(?:[bBrRfFuU]{1,2})?("""
                            r'''"""|\'\'\'|"|'|`)(?:\\.|(?!\1).)*?\1''', re.DOTALL)  # fmt: skip
STATUS_TEXT = re.compile(
    r"returncode|status_code|exit_code|exitcode|exitCode|statusCode|exit_status|\bstatus\b|\bcode\s*\(\s*\)"
    r"|\brc\b|\.\s*ok\b|\bsuccess\s*\(|\bis_ok\b|\bis_err\b|\bunwrap_err\b|\bOk\s*\(|\bErr\s*\(|\btoThrow"
    r"|\brejects\b|\bresolves\b|[Rr]aises\b|\bexpectException|\bassert(?:Ok|Successful|Created|Accepted|NoContent"
    r"|Status|ExitCode|Failed|Forbidden|NotFound|Unauthorized|Unprocessable\w*|ServerError|BadRequest|Conflict)\b"
)
STATUS_OK = re.compile(
    r"\.\s*ok\b|\bsuccess\s*\(|\bis_ok\b|\bOk\s*\(|\bresolves\b|\bassert(?:Ok|Successful|Created|Accepted|NoContent)\b"
)
STATUS_ERR = re.compile(
    r"\bis_err\b|\bunwrap_err\b|\bErr\s*\(|\btoThrow|\brejects\b|[Rr]aises\b|\bexpectException"
    r"|\bassert(?:Failed|Forbidden|NotFound|Unauthorized|Unprocessable\w*|ServerError|BadRequest|Conflict)\b"
)
STATUS_NUMERIC = re.compile(r"code|status|\brc\b|Status|Some")
NEGATED = re.compile(r"!=|\bassert_ne\b|\.\s*not\s*\.|\bassertNot|\bnot\b|[(,]\s*!\s*(?=[\w$(])")
STATUS_INT = re.compile(r"(?<![\w.#$])-?\d+(?![\w.])")


CALL_ARGS = re.compile(
    r"(?<![\w$])(?!(?:in|not|and|or|is|if|else|return|await|match)\b)([A-Za-z_$][\w$]*)\s*(!?)\s*\(([^()]*)\)"
)
KEEP_ARGS = re.compile(r"^(?:Some|Ok|Err|assert\w*|expect\w*|to[A-Z]\w*|check\w*|verify\w*)$")


def drop_call_args(text: str) -> str:
    """Erase the arguments of ordinary calls (`parse(14).returncode`), keeping those of assertion wrappers."""
    for _ in range(8):
        new = CALL_ARGS.sub(
            lambda m: f"{m[1]}{m[2]}[{m[3]}]" if KEEP_ARGS.match(m[1]) else f"{m[1]}{m[2]}[]", text
        )
        if new == text:
            break
        text = new
    return text


def status_sig(texts) -> frozenset[str]:
    """Expected exit codes and success/refusal polarity: an observable, never an abstractable literal."""
    out = set()
    for text in texts:
        bare = STRING_LITERAL.sub("S", text)
        if not STATUS_TEXT.search(bare):
            continue
        ints = STATUS_INT.findall(drop_call_args(bare)) if STATUS_NUMERIC.search(bare) else []
        flags = [f for f, rx in (("ok", STATUS_OK), ("err", STATUS_ERR)) if rx.search(bare)]
        if ints or flags:
            out.add(("!" if NEGATED.search(bare) else "") + ",".join(sorted(ints) + flags))
    return frozenset(out)


PLACEHOLDER = re.compile(r"^(?:#?ID\d+#?|TMP\d+)$")


def atoms(text: str) -> list[str]:
    """Literal lines worth comparing across tests: one per physical or escaped line, eight characters or
    more; shorter pieces are identifiers and flags (`Bash`, `--attempt`) that name no scenario."""
    found = []
    for piece in re.split(r"\n|\\n", text)[:200]:
        piece = piece.strip()
        if len(piece) >= 8 and not PLACEHOLDER.match(piece):
            found.append(piece)
    return found


POLAR = [
    (re.compile(r"\bnot in\b"), "in"),
    (re.compile(r"\bis not\b"), "is"),
    (re.compile(r"!=="), "==="),
    (re.compile(r"!="), "=="),
    (re.compile(r"\.\s*not\s*(?=\.)"), ""),
    (re.compile(r"\bnot\s+"), ""),
    (re.compile(r"(?<=[(,\s])!\s*(?=[\w$(])"), ""),
    (re.compile(r"\bassert_ne\b"), "assert_eq"),
    (re.compile(r"(?<=[a-z])(?:DoesNot|Not)(?=[A-Z])|\b_?not_|_not\b"), ""),
    (re.compile(r"\bis_(?:none|err|empty|ok|some)\b"), "is_some"),
    (re.compile(r"\bassert(?:False|True)\b"), "assertTrue"),
    (re.compile(r"\btoBe(?:Falsy|Truthy|Null|Undefined|Defined)\b"), "toBeTruthy"),
    (re.compile(r"\b(?:True|False|None|true|false)\b"), "BOOL"),
    (re.compile(r"\b(?:startswith|endswith|starts_with|ends_with|startsWith|endsWith|contains|includes|"
                r"toContain|toMatch|toBe|toEqual|toStrictEqual|assertStringContainsString|assertStringStartsWith|"
                r"assertStringEndsWith|assertSame|assertEquals|assertEqual|assertIn)\b"), "REL"),
]  # fmt: skip
REL_FORMS = [
    re.compile(r"^assert _ (?:in|==|is) (.+)$"),
    re.compile(r"^assert (.+?) (?:==|in|is) _$"),
    re.compile(r"^assert (.+?)\.REL\(_\)$"),
    re.compile(r"^assert_eq (?:! )?\( (.+?) , [SN] \)$"),
    re.compile(r"^assert_eq (?:! )?\( [SN] , (.+?) \)$"),
    re.compile(r"^assert (?:! )?\( (.+?) \. REL \( [SN] \) \)$"),
    re.compile(r"^expect \( (.+?) \) \. REL \( [SN] \)$"),
]


def polar(shape: str) -> str:
    """An assertion shape with polarity and check strength erased: in/not in, ==/!=, contains/starts_with."""
    for rx, repl in POLAR:
        shape = rx.sub(repl, shape)
    for rx in REL_FORMS:
        m = rx.match(shape)
        if m:
            return f"REL({m.group(1)})"
    return shape


CALLEE = re.compile(r"([A-Za-z_$][\w$]*(?:\s*(?:\.|->|::|\?->)\s*[A-Za-z_$][\w$]*)*)\s*!?\s*\(")
ASSIGNED = re.compile(
    r"^(?:(?:let|const|var|mut)\s+)*[\w$\s,()\[\]*.:>-]*?(?<![=!<>])=(?![=>])\s*(?:await\s+)?"
)


def head(shape: str) -> str:
    """The callee a setup statement runs (`world.write`), else the whole statement."""
    body = ASSIGNED.sub("", shape, count=1).strip()
    m = CALLEE.match(body)
    return re.sub(r"\s+", "", m.group(1)) if m else shape


def receiver(shape: str) -> str | None:
    """The object a trailing method call acts on (`(root / _).chmod(_)` -> `(root / _)`), else None."""
    body = ASSIGNED.sub("", shape, count=1).strip().rstrip(";").rstrip()
    if not body.endswith(")"):
        return None
    depth = 0
    for i in range(len(body) - 1, -1, -1):
        depth += {")": 1, "(": -1}.get(body[i], 0)
        if depth == 0:
            m = re.search(r"(?:\.|->|\?->)\s*[A-Za-z_$][\w$]*\s*$", body[:i])
            return re.sub(r"\s+", "", body[: m.start()]) if m and m.start() > 0 else None
    return None


SUBJECT = [
    re.compile(r"^assert .+? (?:not in|in) (.+)$"),
    re.compile(r"^assert (?:not )?(.+?) (?:==|!=|is not|is) .+$"),
    re.compile(r"^assert (?:not )?(.+?)\.(?:startswith|endswith)\(.*\)$"),
    re.compile(r"^assert (?:! )?\( (?:! )?(.+?) \. (?:contains|starts_with|ends_with) \( .*$"),
    re.compile(r"^assert_(?:eq|ne) ! \( (.+?) , .*$"),
    re.compile(r"^expect \( (.+?) \) \..*$"),
]


def subject(shape: str) -> str:
    """What an assertion inspects (`v0.stderr` in `assert _ in v0.stderr`), else the whole shape."""
    for rx in SUBJECT:
        m = rx.match(shape)
        if m:
            return m.group(1)
    return shape


# ---------------------------------------------------------------- Python

ASSERT_CALL = re.compile(r"^_*(?:assert|expect|verify|check)\w*$")
FAIL_OWNERS = {"pytest", "self", "cls", "unittest"}
RAISES_CTX = re.compile(r"(?:^|\.)(?:raises|warns|deprecated_call|assertRaises\w*|assertWarns\w*)$")
SKIP_CALL = re.compile(r"(?:^|\.)(?:skip|skipTest|importorskip|xfail)$")
READER_CALLS = {
    "loads", "load", "read_text", "read_bytes", "exists", "is_file", "is_dir", "is_symlink",
    "stat", "lstat", "json_lines", "readlines", "splitlines", "decode", "encode", "keys",
    "values", "items", "get", "len", "sorted", "list", "dict", "set", "tuple", "str", "bytes",
    "int", "float", "bool", "fspath", "glob", "rglob", "iterdir", "read", "strip", "split",
    "lower", "upper", "startswith", "endswith", "count", "index", "find", "hexdigest",
    "sha256", "any", "all", "sum", "min", "max", "isinstance", "type", "repr", "format",
    "join", "replace", "resolve", "readlink", "listdir", "with_name", "with_suffix", "joinpath",
    "relative_to", "as_posix", "read_json", "getvalue",
}  # fmt: skip
READER_PREFIX = re.compile(r"^_*(?:read|load|parse|show|lines|json|manifest|collect)")
DIGIT_RUN = re.compile(r"(?<![A-Za-z0-9])\d{2,}(?!\d)")
STATUS_WORDS = re.compile(r"returncode|[Ss]tatus|exit_code|\.code\b|\brc\b")


def call_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def dotted(node: ast.AST) -> str:
    return text_of(node)


def clone(node):
    """Copy an AST far faster than copy.deepcopy; scalars and context singletons are shared."""
    new = node.__class__.__new__(node.__class__)
    fields = new.__dict__
    for key, value in node.__dict__.items():
        if isinstance(value, list):
            fields[key] = [clone(item) if isinstance(item, ast.AST) else item for item in value]
        elif isinstance(value, ast.AST) and not isinstance(value, ast.expr_context):
            fields[key] = clone(value)
        else:
            fields[key] = value
    return new


def walk(root: ast.AST):
    """Pre-order walk in source order; much cheaper than ast.walk."""
    stack = [root]
    while stack:
        node = stack.pop()
        yield node
        for name in reversed(node._fields):
            value = getattr(node, name, None)
            if isinstance(value, list):
                stack.extend(v for v in reversed(value) if isinstance(v, ast.AST))
            elif isinstance(value, ast.AST) and not isinstance(value, ast.expr_context):
                stack.append(value)


def text_of(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except (ValueError, RecursionError):  # 3.11 cannot unparse a backslash inside an f-string part
        return ast.dump(node, annotate_fields=False)


class Subst(ast.NodeTransformer):
    def __init__(self, mapping: dict[str, ast.expr]) -> None:
        self.mapping = mapping

    def visit_Name(self, node: ast.Name) -> ast.AST:
        if isinstance(node.ctx, ast.Load) and node.id in self.mapping:
            return clone(self.mapping[node.id])
        return node


def literal(node: ast.AST) -> tuple[bool, object]:
    try:
        return True, ast.literal_eval(node)
    except Exception:  # noqa: BLE001 - literal_eval raises several types
        return False, None


COMPARE_OPS = {
    ast.Eq: lambda a, b: a == b,
    ast.NotEq: lambda a, b: a != b,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
    ast.Is: lambda a, b: a is b,
    ast.IsNot: lambda a, b: a is not b,
    ast.Lt: lambda a, b: a < b,
    ast.LtE: lambda a, b: a <= b,
    ast.Gt: lambda a, b: a > b,
    ast.GtE: lambda a, b: a >= b,
}


def const_eval(node: ast.AST) -> tuple[bool, object]:
    """Evaluate a test expression that parametrize substitution made constant."""
    ok, value = literal(node)
    if ok:
        return True, value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        ok, value = const_eval(node.operand)
        return ok, (not value) if ok else None
    if isinstance(node, ast.BoolOp):
        values = []
        for item in node.values:
            ok, value = const_eval(item)
            if not ok:
                return False, None
            values.append(value)
        return True, all(values) if isinstance(node.op, ast.And) else any(values)
    if isinstance(node, ast.Compare):
        ok, left = const_eval(node.left)
        if not ok:
            return False, None
        for op, right_node in zip(node.ops, node.comparators, strict=True):
            ok, right = const_eval(right_node)
            fn = COMPARE_OPS.get(type(op))
            if not ok or fn is None:
                return False, None
            try:
                if not fn(left, right):
                    return True, False
            except TypeError:
                return False, None
            left = right
        return True, True
    return False, None


class FoldIfExp(ast.NodeTransformer):
    def visit_IfExp(self, node: ast.IfExp) -> ast.AST:
        self.generic_visit(node)
        ok, value = const_eval(node.test)
        if ok:
            return node.body if value else node.orelse
        return node


def fold(stmts: list[ast.stmt]) -> list[ast.stmt]:
    out: list[ast.stmt] = []
    for stmt in stmts:
        stmt = FoldIfExp().visit(stmt)
        if isinstance(stmt, ast.If):
            ok, value = const_eval(stmt.test)
            if ok:
                out.extend(fold(stmt.body if value else stmt.orelse))
                continue
        for name in ("body", "orelse", "finalbody"):
            if isinstance(getattr(stmt, name, None), list):
                setattr(stmt, name, fold(getattr(stmt, name)))
        if isinstance(stmt, ast.Try | ast.TryStar):
            for handler in stmt.handlers:
                handler.body = fold(handler.body)
        out.append(stmt)
    return out


def marker(name: str, *args: ast.expr) -> ast.stmt:
    return ast.Expr(value=ast.Call(func=ast.Name(id=name, ctx=ast.Load()), args=list(args), keywords=[]))


def is_assert_stmt(stmt: ast.stmt) -> bool:
    if isinstance(stmt, ast.Assert):
        return True
    if isinstance(stmt, ast.Expr):
        value = stmt.value.value if isinstance(stmt.value, ast.Await) else stmt.value
        return isinstance(value, ast.Call) and is_assert_call(value)
    return False


def is_assert_call(node: ast.Call) -> bool:
    """`assert*`/`expect*`/... calls, and `fail()` only as pytest's or unittest's: `world.fail(x)` is setup."""
    name = call_name(node)
    if name == "fail":
        func = node.func
        return isinstance(func, ast.Name) or (
            isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Name)
            and func.value.id in FAIL_OWNERS
        )
    return bool(ASSERT_CALL.match(name))


RESULT_ATTRS = {"returncode", "status_code", "exit_code", "ok", "stdout", "stderr", "combined", "output"}


PURE_CALLS = {"match", "fullmatch", "search", "findall", "compile", "sub", "dumps", "approx", "call", "ANY"}


def acting(test: ast.AST, wrapper: ast.AST | None = None) -> bool:
    """True when the assertion itself exercises code: `assert run(...).returncode == 0`, or
    `assert f("input") == 1` (a non-reader call given a string literal inside the assertion)."""
    for n in walk(test):
        if (
            isinstance(n, ast.Attribute)
            and n.attr in RESULT_ATTRS
            and isinstance(n.value, ast.Call)
            and call_name(n.value) not in READER_CALLS
        ):
            return True
        if isinstance(n, ast.Call) and n is not wrapper:
            name = call_name(n)
            if (
                name in READER_CALLS
                or name in PURE_CALLS
                or READER_PREFIX.match(name)
                or ASSERT_CALL.match(name)
            ):
                continue
            if any(carries_literal(a) for a in [*n.args, *(k.value for k in n.keywords)]):
                return True
    return False


def blob_atoms(text: str) -> list[str]:
    """Atoms of the string literals inside a collapsed container, else of its text."""
    try:
        tree = ast.parse(text, mode="eval")
    except SyntaxError:
        return atoms(text)
    found: list[str] = []
    for n in walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str | bytes):
            found += atoms(n.value if isinstance(n.value, str) else n.value.decode("latin-1"))
    return found


def carries_literal(node: ast.AST) -> bool:
    """A call argument that supplies input text: a literal or f-string, also nested (`[call("bash", command=...)]`)."""
    return any(
        isinstance(n, ast.JoinedStr)
        or isinstance(n, ast.Constant)
        and isinstance(n.value, str | bytes | Blob)
        for n in walk(node)
    )


def selectors(stmt: ast.AST) -> set[int]:
    """Literals that pick what to read (`text.index("### Phase 3:")`, `read(root / "x.md")`): fixture, not signal."""
    chosen: set[int] = set()
    for node in walk(stmt):
        if isinstance(node, ast.Call) and observer(node):
            picked = [*node.args, *(k.value for k in node.keywords)]
            if isinstance(node.func, ast.Attribute):
                picked.append(node.func.value)  # `(root / "x.md").read_text()`
            for arg in picked:
                if isinstance(arg, ast.Constant | ast.BinOp):
                    chosen.update(id(n) for n in walk(arg) if isinstance(n, ast.Constant))
    return chosen


def observer(node: ast.Call) -> bool:
    """A call that only reads, formats, or asserts: a test made of these alone exercises no code."""
    name = call_name(node)
    return (
        name.startswith("__")
        or name in READER_CALLS
        or name in PURE_CALLS
        or bool(READER_PREFIX.match(name))
        or is_assert_call(node)
    )


def is_skip_guard(stmt: ast.stmt) -> bool:
    if not isinstance(stmt, ast.If) or len(stmt.body) != 1:
        return False
    only = stmt.body[0]
    if isinstance(only, ast.Return):
        return True
    return (
        isinstance(only, ast.Expr)
        and isinstance(only.value, ast.Call)
        and bool(SKIP_CALL.search(dotted(only.value.func)))
    )


def flatten(stmts: list[ast.stmt]) -> list[tuple[str, ast.stmt]]:
    out: list[tuple[str, ast.stmt]] = []
    for stmt in stmts:
        if isinstance(stmt, ast.Pass) or (
            isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant)
        ):
            continue
        if is_skip_guard(stmt):
            out.extend(flatten(stmt.orelse))  # type: ignore[attr-defined]
            continue
        if isinstance(stmt, ast.If):
            out.append(("action", ast.If(test=stmt.test, body=[ast.Pass()], orelse=[])))
            out.extend(flatten(stmt.body))
            if stmt.orelse:
                out.append(("action", marker("__else__")))
                out.extend(flatten(stmt.orelse))
            out.append(("action", marker("__end__")))
        elif isinstance(stmt, ast.For | ast.AsyncFor | ast.While) and all(
            is_assert_stmt(s) for s in stmt.body
        ):
            loop = clone(stmt)
            loop.body = [
                ast.Assert(test=s.test, msg=None) if isinstance(s, ast.Assert) else s for s in loop.body
            ]
            out.append(("assert", loop))
        elif isinstance(stmt, ast.For | ast.AsyncFor):
            out.append(("action", marker("__for__", stmt.target, stmt.iter)))
            out.extend(flatten(stmt.body))
            out.append(("action", marker("__end__")))
        elif isinstance(stmt, ast.While):
            out.append(("action", marker("__while__", stmt.test)))
            out.extend(flatten(stmt.body))
            out.append(("action", marker("__end__")))
        elif isinstance(stmt, ast.With | ast.AsyncWith):
            others = []
            for item in stmt.items:
                ctx = item.context_expr
                if isinstance(ctx, ast.Call) and RAISES_CTX.search(dotted(ctx.func)):
                    out.append(("assert", ast.Expr(value=ctx)))
                else:
                    others.append(item)
            if others:
                out.append(("action", ast.With(items=others, body=[ast.Pass()], lineno=0, type_comment=None)))
            out.extend(flatten(stmt.body))
            if others:
                out.append(("action", marker("__end__")))
        elif isinstance(stmt, ast.Try | ast.TryStar):
            out.extend(flatten(stmt.body))
            for handler in stmt.handlers:
                out.append(("action", marker("__except__", *([handler.type] if handler.type else []))))
                out.extend(flatten(handler.body))
            out.extend(flatten(stmt.orelse))
            if stmt.finalbody:
                out.append(("action", marker("__finally__")))
                out.extend(flatten(stmt.finalbody))
        elif isinstance(stmt, ast.Assert):
            if acting(stmt.test):
                copy = ast.Expr(value=stmt.test)
                copy.acting_copy = True  # type: ignore[attr-defined]
                out.append(("action", copy))
            out.append(("assert", ast.Assert(test=stmt.test, msg=None)))
        elif is_assert_stmt(stmt):
            call = stmt.value.value if isinstance(stmt.value, ast.Await) else stmt.value  # type: ignore[attr-defined]
            if acting(stmt, call):
                copy = clone(stmt)
                copy.acting_copy = True
                out.append(("action", copy))
            out.append(("assert", stmt))
        else:
            out.append(("action", stmt))
    return out


def body_names(stmts: list[ast.stmt]) -> tuple[Counter[str], set[str], bool]:
    """Store counts, loaded names, and whether any if/ternary exists, in one pass."""
    counts: Counter[str] = Counter()
    loads: set[str] = set()
    branches = False
    for root in stmts:
        for node in walk(root):
            if isinstance(node, ast.Name):
                if isinstance(node.ctx, ast.Load):
                    loads.add(node.id)
                else:
                    counts[node.id] += 1
            elif isinstance(node, ast.If | ast.IfExp):
                branches = True
            elif isinstance(node, ast.arg):
                counts[node.arg] += 2
            elif isinstance(node, ast.ExceptHandler) and node.name:
                counts[node.name] += 2
            elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
                counts[node.target.id] += 1
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                counts[node.name] += 2
    return counts, loads, branches


def loaded_names(node: ast.AST) -> set[str]:
    return {n.id for n in walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}


INLINABLE = (
    ast.Name, ast.Attribute, ast.Subscript, ast.BinOp, ast.Constant, ast.JoinedStr,
    ast.FormattedValue, ast.Tuple, ast.UnaryOp, ast.Compare, ast.BoolOp, ast.Slice, ast.Starred,
    ast.operator, ast.unaryop, ast.cmpop, ast.boolop,
)  # fmt: skip


def call_free(node: ast.AST) -> bool:
    return all(isinstance(n, INLINABLE) for n in walk(node))


def reader_only(node: ast.AST) -> bool:
    calls = [n for n in walk(node) if isinstance(n, ast.Call)]
    return bool(calls) and all(
        call_name(c) in READER_CALLS or READER_PREFIX.match(call_name(c)) for c in calls
    )


def single_target(stmt: ast.stmt) -> str | None:
    if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
        return stmt.targets[0].id
    if isinstance(stmt, ast.AnnAssign) and stmt.value is not None and isinstance(stmt.target, ast.Name):
        return stmt.target.id
    return None


def inline(flat: list[tuple[str, ast.stmt]], stores: Counter[str]) -> list[tuple[str, ast.stmt]]:
    """Inline call-free single bindings, then observation bindings used only by assertions."""
    mapping: dict[str, ast.expr] = {}
    first: list[tuple[str, ast.stmt, set[str]]] = []
    for kind, stmt in flat:
        loads = loaded_names(stmt)
        if mapping and loads & mapping.keys():
            stmt = Subst(mapping).visit(stmt)
            loads = loaded_names(stmt)
        name = single_target(stmt)
        value = getattr(stmt, "value", None)
        if kind == "action" and name and stores[name] == 1 and value is not None and call_free(value):
            mapping[name] = value
            continue
        first.append((kind, stmt, loads))

    candidates = {
        name
        for kind, stmt, _ in first
        if kind == "action"
        and (name := single_target(stmt))
        and stores[name] == 1
        and reader_only(stmt.value)  # type: ignore[union-attr]
    }
    changed = True
    while changed:
        changed = False
        for kind, stmt, loads in first:
            if kind == "assert" or single_target(stmt) in candidates:
                continue
            used = loads & candidates
            if used:
                candidates -= used
                changed = True
    # A read taken before a later action is a snapshot, not an observation of the result: keep it.
    for index, (kind, stmt, _) in enumerate(first):
        name = single_target(stmt)
        if kind != "action" or name not in candidates:
            continue
        uses = [i for i, (_, _, loads) in enumerate(first) if i > index and name in loads]
        between = first[index + 1 : max(uses, default=index) + 1]
        if any(k == "action" and single_target(st) not in candidates for k, st, _ in between):
            candidates.discard(name)
    mapping = {}
    out: list[tuple[str, ast.stmt]] = []
    for kind, stmt, loads in first:
        if mapping and loads & mapping.keys():
            stmt = Subst(mapping).visit(stmt)
        name = single_target(stmt)
        if kind == "action" and name in candidates:
            mapping[name] = stmt.value  # type: ignore[union-attr, assignment]
            continue
        out.append((kind, stmt))
    return out


class Blob:
    """A Constant payload that unparses verbatim: a collapsed literal container or a placeholder."""

    __slots__ = ("text",)

    def __init__(self, text: str) -> None:
        self.text = text

    def __repr__(self) -> str:
        return self.text

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Blob) and other.text == self.text

    def __hash__(self) -> int:
        return hash(self.text)


def all_literal(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, ast.List | ast.Tuple | ast.Set):
        return all(all_literal(e) for e in node.elts)
    if isinstance(node, ast.Dict):
        return all(k is not None and all_literal(k) for k in node.keys) and all(
            all_literal(v) for v in node.values
        )
    if isinstance(node, ast.UnaryOp):
        return all_literal(node.operand)
    return False


def replace_children(root: ast.AST, pick) -> ast.AST:
    """Replace, in place, every maximal subexpression for which pick() returns a node."""
    stack = [root]
    while stack:
        node = stack.pop()
        for name in node._fields:
            value = getattr(node, name, None)
            if isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, ast.expr) and (new := pick(item)) is not None:
                        value[i] = new
                    elif isinstance(item, ast.AST):
                        stack.append(item)
            elif isinstance(value, ast.expr):
                if (new := pick(value)) is not None:
                    setattr(node, name, new)
                else:
                    stack.append(value)
            elif isinstance(value, ast.AST) and not isinstance(value, ast.expr_context):
                stack.append(value)
    return root


def collapse(root: ast.AST) -> ast.AST:
    """Fold large literal containers into one Constant so later passes visit one node, not hundreds."""

    def pick(node: ast.expr) -> ast.expr | None:
        if isinstance(node, ast.List | ast.Tuple | ast.Set | ast.Dict) and all_literal(node):
            size = sum(1 for _ in walk(node))
            if size > 12:
                return ast.Constant(value=Blob(text_of(node)))
        return None

    return replace_children(root, pick)


UNDERSCORE = ast.Name(id="_", ctx=ast.Load())
Unparser = getattr(ast, "_Unparser", None)


if Unparser is not None:

    class ShapeUnparser(Unparser):  # type: ignore[misc, valid-type]
        """Unparse with every literal (and f-string) written as `_`, without copying the tree."""

        def traverse(self, node):
            if isinstance(node, ast.expr) and abstracted(node):
                self.write("_")
                return None
            return super().traverse(node)


def literal_expr(node: ast.AST) -> bool:
    """A literal, or an expression built only from literals (`"row\\n" + "x" * 5200`): one table cell."""
    if isinstance(node, ast.BinOp):
        return literal_expr(node.left) and literal_expr(node.right)
    if isinstance(node, ast.UnaryOp):
        return literal_expr(node.operand)
    if isinstance(node, ast.List | ast.Tuple | ast.Set):
        return all(literal_expr(e) for e in node.elts)
    return all_literal(node)


def abstracted(node: ast.expr) -> bool:
    """A literal a table row could vary; True/False/None stay, because they carry assertion polarity."""
    if isinstance(node, ast.Constant) and (node.value is None or isinstance(node.value, bool)):
        return False
    return isinstance(node, ast.JoinedStr) or literal_expr(node)


def shape_of(stmt: ast.stmt) -> str:
    if Unparser is not None:
        try:
            return ShapeUnparser().visit(stmt)
        except (ValueError, RecursionError):
            pass

    def pick(node: ast.expr) -> ast.expr | None:
        return UNDERSCORE if abstracted(node) else None

    return text_of(replace_children(clone(stmt), pick))


def placeholders(flat: list[tuple[str, ast.stmt]], tmp_roots: bool) -> None:
    """Replace tmp path segments and threaded identifiers in place (see module docstring)."""
    if tmp_roots:
        seen: dict[str, str] = {}
        for _, stmt in flat:
            for node in walk(stmt):
                if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
                    root = node.left
                    while isinstance(root, ast.BinOp) and isinstance(root.op, ast.Div):
                        root = root.left
                    right = node.right
                    if (
                        isinstance(root, ast.Name)
                        and "tmp" in root.id.lower()
                        and isinstance(right, ast.Constant)
                        and isinstance(right.value, str)
                    ):
                        right.value = Blob(seen.setdefault(right.value, f"TMP{len(seen)}"))
    counts: Counter[str] = Counter()
    compared: set[str] = set()
    for kind, stmt in flat:
        if getattr(stmt, "acting_copy", False):
            continue
        top = getattr(stmt, "value", None)
        for node in walk(stmt):
            if isinstance(node, ast.Constant):
                v = node.value
                if isinstance(v, int) and not isinstance(v, bool) and abs(v) >= 10:
                    values = [str(abs(v))]
                elif isinstance(v, str):
                    values = DIGIT_RUN.findall(v)
                elif isinstance(v, bytes):
                    values = DIGIT_RUN.findall(v.decode("latin-1"))
                else:
                    continue
                if kind == "action":
                    counts.update(values)
            elif kind == "assert" and isinstance(node, ast.Compare | ast.Call):
                operands = [node.left, *node.comparators] if isinstance(node, ast.Compare) else node.args
                if isinstance(node, ast.Call) and node is not top:
                    continue
                if not STATUS_WORDS.search(text_of(node)):
                    continue
                for operand in operands:
                    if isinstance(operand, ast.Constant) and isinstance(operand.value, int):
                        compared.add(str(abs(operand.value)))
    ids: dict[str, str] = {}
    for value in counts:  # insertion order is first appearance
        if counts[value] >= 2 and value not in compared:
            ids[value] = f"ID{len(ids)}"
    if not ids:
        return

    def sub(text: str) -> str:
        return DIGIT_RUN.sub(lambda m: f"#{ids[m.group()]}#" if m.group() in ids else m.group(), text)

    for _, stmt in flat:
        for node in walk(stmt):
            if isinstance(node, ast.Constant):
                v = node.value
                if isinstance(v, int) and not isinstance(v, bool) and str(abs(v)) in ids:
                    node.value = Blob(ids[str(abs(v))])
                elif isinstance(v, str):
                    node.value = sub(v)
                elif isinstance(v, bytes):
                    node.value = sub(v.decode("latin-1")).encode("latin-1")


def split_kwargs(
    stmt: ast.stmt, text: str, defaults: dict[str, dict[str, object]]
) -> tuple[str, tuple[tuple[tuple[str, str], ...], ...]]:
    """Positional text plus per-call keywords; `!key` marks a keyword whose callee default is known."""
    calls = [n for n in walk(stmt) if isinstance(n, ast.Call)]
    if not any(c.keywords for c in calls):
        return text, tuple(() for _ in calls)
    node = clone(stmt)
    found: list[tuple[tuple[str, str], ...]] = []
    stack: list[ast.AST] = [node]
    while stack:
        n = stack.pop()
        if isinstance(n, ast.Call):
            known = defaults.get(n.func.id, {}) if isinstance(n.func, ast.Name) else {}
            found.append(
                tuple(
                    sorted(
                        (f"!{k.arg}" if k.arg in known else k.arg or f"**{i}", text_of(k.value))
                        for i, k in enumerate(n.keywords)
                    )
                )
            )
            n.keywords = []
        stack.extend(reversed([c for c in ast.iter_child_nodes(n) if not isinstance(c, ast.expr_context)]))
    return text_of(node), tuple(found)


def module_constants(tree: ast.Module) -> dict[str, ast.expr]:
    counts: Counter[str] = Counter()
    values: dict[str, ast.expr] = {}
    for stmt in tree.body:
        name = single_target(stmt)
        if name:
            counts[name] += 1
            value = stmt.value  # type: ignore[union-attr]
            if value is not None and all_literal(value):
                values[name] = value
    return {k: v for k, v in values.items() if counts[k] == 1}


def module_defaults(tree: ast.Module) -> dict[str, dict[str, object]]:
    """Literal keyword defaults of module-level helpers, so passing a default explicitly is a no-op."""
    found: dict[str, dict[str, object]] = {}
    for stmt in tree.body:
        if isinstance(stmt, ast.FunctionDef | ast.AsyncFunctionDef):
            args = stmt.args
            positional = [*args.posonlyargs, *args.args]
            pairs = list(zip(positional[len(positional) - len(args.defaults) :], args.defaults, strict=True))
            pairs += [(a, d) for a, d in zip(args.kwonlyargs, args.kw_defaults, strict=True) if d is not None]
            values = {}
            for arg, default in pairs:
                ok, value = literal(default)
                if ok:
                    values[arg.arg] = value
            if args.kwarg is not None:
                values.update(dict_defaults(stmt, args.kwarg.arg))
            if values:
                found[stmt.name] = values
    # A helper that forwards **extra to another helper inherits that helper's keyword defaults.
    for _ in range(3):
        for stmt in tree.body:
            if not isinstance(stmt, ast.FunctionDef | ast.AsyncFunctionDef) or stmt.args.kwarg is None:
                continue
            extra = stmt.args.kwarg.arg
            for node in walk(stmt):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id in found
                    and any(
                        k.arg is None and isinstance(k.value, ast.Name) and k.value.id == extra
                        for k in node.keywords
                    )
                ):
                    inherited = {
                        k: v for k, v in found[node.func.id].items() if k not in found.get(stmt.name, {})
                    }
                    if inherited:
                        found.setdefault(stmt.name, {}).update(inherited)
    return found


def dict_defaults(func: ast.FunctionDef | ast.AsyncFunctionDef, extra: str) -> dict[str, object]:
    """Keys of a literal dict that `**extra` is merged over (`body.update(extra)` or `{**d, **extra}`)."""
    merged = any(
        isinstance(n, ast.Call)
        and call_name(n) == "update"
        and any(isinstance(a, ast.Name) and a.id == extra for a in n.args)
        or isinstance(n, ast.Dict)
        and any(
            k is None and isinstance(v, ast.Name) and v.id == extra
            for k, v in zip(n.keys, n.values, strict=True)
        )
        for n in walk(func)
    )
    if not merged:
        return {}
    values: dict[str, object] = {}
    seen: Counter[str] = Counter()
    for node in walk(func):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values, strict=True):
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    seen[key.value] += 1
                    ok, literal_value = literal(value)
                    if ok:
                        values[key.value] = literal_value
        elif (
            isinstance(node, ast.Subscript)
            and isinstance(node.ctx, ast.Store)
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            seen[node.slice.value] += 1
    # A key the helper assigns more than once has a computed default: treat it as unknown.
    return {k: v for k, v in values.items() if seen[k] == 1}


def drop_default_kwargs(stmts: list[ast.stmt], defaults: dict[str, dict[str, object]]) -> None:
    for stmt in stmts:
        for node in walk(stmt):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in defaults:
                known = defaults[node.func.id]
                kept = []
                for kw in node.keywords:
                    if kw.arg in known:
                        ok, value = literal(kw.value)
                        # Exact type, so True does not stand in for a default of 1.
                        if ok and type(value) is type(known[kw.arg]) and value == known[kw.arg]:  # noqa: E721
                            continue
                    kept.append(kw)
                node.keywords = kept


def parametrize_cases(
    func: ast.FunctionDef | ast.AsyncFunctionDef, constants: dict[str, ast.expr]
) -> tuple[list[tuple[str, dict[str, ast.expr]]], set[str], set[str], bool]:
    """Return (cases, expanded names, symbolic names, parametrized?)."""
    cases: list[tuple[str, dict[str, ast.expr]]] = [("", {})]
    expanded: set[str] = set()
    symbolic: set[str] = set()
    parametrized = False
    for deco in func.decorator_list:
        if not isinstance(deco, ast.Call) or not dotted(deco.func).endswith("parametrize") or not deco.args:
            continue
        parametrized = True
        names_node = deco.args[0]
        ok, names_value = literal(names_node)
        if not ok:
            continue
        if isinstance(names_value, str):
            names = [n.strip() for n in names_value.split(",") if n.strip()]
        else:
            names = [str(n) for n in names_value]
        values_node = deco.args[1] if len(deco.args) > 1 else None
        for kw in deco.keywords:
            if kw.arg == "argvalues":
                values_node = kw.value
        if isinstance(values_node, ast.Name) and values_node.id in constants:
            values_node = constants[values_node.id]
        ids_node = next((kw.value for kw in deco.keywords if kw.arg == "ids"), None)
        ids_ok, ids_value = literal(ids_node) if ids_node is not None else (False, None)
        if not isinstance(values_node, ast.List | ast.Tuple):
            symbolic.update(names)
            continue
        rows: list[tuple[str, dict[str, ast.expr]]] = []
        for index, element in enumerate(values_node.elts):
            label = None
            if isinstance(element, ast.Call) and call_name(element) == "param":
                for kw in element.keywords:
                    if kw.arg == "id":
                        ok, label = literal(kw.value)
                element = (
                    element.args[0] if len(names) == 1 and element.args else ast.Tuple(elts=element.args)
                )
            if len(names) == 1:
                values = [element]
            elif isinstance(element, ast.Tuple | ast.List) and len(element.elts) == len(names):
                values = list(element.elts)
            else:
                symbolic.update(names)
                rows = []
                break
            if label is None and ids_ok and isinstance(ids_value, list | tuple) and index < len(ids_value):
                label = ids_value[index]
            if label is None:
                simple = [literal(v) for v in values]
                label = (
                    "-".join(str(v) for _, v in simple)
                    if all(ok and isinstance(v, str | int | float | bool | None) for ok, v in simple)
                    else str(index)
                )
            rows.append((str(label), dict(zip(names, values, strict=True))))
        if not rows:
            continue
        expanded.update(names)
        cases = [
            ("-".join(p for p in (a, b) if p), {**ma, **mb})
            for (a, ma), (b, mb) in itertools.product(cases, rows)
        ][:64]
    return cases, expanded, symbolic, parametrized


def py_unit(
    path: str,
    qual: str,
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    base: list[ast.stmt],
    label: str,
    subst: dict[str, ast.expr],
    constants: dict[str, ast.expr],
    defaults: dict[str, dict[str, object]],
    fixtures: tuple[str, ...],
    fixture_keys: tuple[str, ...],
    parametrized: bool,
) -> Unit:
    body = [Subst(subst).visit(clone(s)) if subst else clone(s) for s in base]
    stores, used, branches = body_names(body)
    cmap = {k: v for k, v in constants.items() if k in used and k not in stores and k not in fixtures}
    if cmap:
        body = [Subst(cmap).visit(s) for s in body]
    if branches and (subst or cmap):
        body = fold(body)
        stores = body_names(body)[0]
    if defaults:
        drop_default_kwargs(body, defaults)
    flat = inline(flatten(body), stores)

    fixture_set = set(fixtures)
    mapping: dict[str, str] = {}
    for _, stmt in sorted(flat, key=lambda item: item[0] == "assert"):
        for node in walk(stmt):
            if isinstance(node, ast.Name):
                if node.id in stores and node.id not in fixture_set:
                    node.id = mapping.setdefault(node.id, f"v{len(mapping)}")
            elif isinstance(node, ast.arg) and node.arg in stores and node.arg not in fixture_set:
                node.arg = mapping.setdefault(node.arg, f"v{len(mapping)}")
    placeholders(flat, any("tmp" in f.lower() for f in fixtures))

    texts = [text_of(stmt) for _, stmt in flat]
    shapes = [shape_of(stmt) for _, stmt in flat]
    inputs: set[str] = set()
    needles: set[str] = set()
    real_act = False
    for kind, stmt in flat:
        bucket = needles if kind == "assert" else inputs
        chosen = selectors(stmt)
        for node in walk(stmt):
            if isinstance(node, ast.Constant) and id(node) in chosen:
                continue
            if isinstance(node, ast.Constant):
                v = node.value
                if isinstance(v, str):
                    bucket.update(atoms(v))
                elif isinstance(v, Blob):
                    bucket.update(blob_atoms(v.text))
                elif isinstance(v, bytes):
                    bucket.update(atoms(v.decode("latin-1")))
            # A module helper called with only fixtures (`spine_text(repo_root)`) loads a fixture.
            elif (
                kind == "action"
                and isinstance(node, ast.Call)
                and not observer(node)
                and (
                    isinstance(node.func, ast.Attribute)
                    or any(carries_literal(a) for a in [*node.args, *(k.value for k in node.keywords)])
                )
            ):
                real_act = True
    last_assert = max((i for i, (k, _) in enumerate(flat) if k == "assert"), default=-1)
    act = -1
    for i, (kind, _) in enumerate(flat):
        if kind == "action" and (last_assert < 0 or i < last_assert) and not texts[i].startswith("__"):
            act = i
    actions, pos, kwargs, action_shape = [], [], [], []
    pre, post, assert_shape = set(), set(), []
    for i, (kind, stmt) in enumerate(flat):
        if kind == "assert":
            (pre if i < act else post).add(texts[i])
            assert_shape.append(shapes[i])
        else:
            actions.append(texts[i])
            p, k = split_kwargs(stmt, texts[i], defaults)
            pos.append(p)
            kwargs.extend(k)
            action_shape.append(shapes[i])
    return Unit(
        path=path,
        line=func.lineno,
        func=f"{path}::{qual}",
        name=f"{qual}[{label}]" if label else qual,
        fixtures=fixture_keys,
        actions=tuple(actions),
        action_pos=tuple(pos),
        action_kwargs=tuple(kwargs),
        pre=frozenset(pre),
        post=frozenset(post),
        action_shape=tuple(action_shape),
        assert_shape=tuple(sorted(assert_shape)),
        act_shape=shapes[act] if act >= 0 else "",
        setup_shape=tuple(shapes[i] for i in range(act + 1) if flat[i][0] == "action"),
        params=parametrized,
        status=status_sig(texts[i] for i, (kind, _) in enumerate(flat) if kind == "assert"),
        inputs=frozenset(inputs),
        needles=frozenset(needles),
        real_act=real_act,
    )


def scan_python(path: str, text: str, part: int = 0, parts: int = 1) -> list[Unit]:
    tree = ast.parse(text)
    constants = {k: collapse(ast.Expr(value=clone(v))).value for k, v in module_constants(tree).items()}  # type: ignore[attr-defined]
    defaults = module_defaults(tree)
    local_fixtures = {
        stmt.name
        for stmt in tree.body
        if isinstance(stmt, ast.FunctionDef | ast.AsyncFunctionDef)
        and any("fixture" in dotted(d.func if isinstance(d, ast.Call) else d) for d in stmt.decorator_list)
    }
    funcs: list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]] = []
    for stmt in tree.body:
        if isinstance(stmt, ast.FunctionDef | ast.AsyncFunctionDef) and stmt.name.startswith("test"):
            funcs.append((stmt.name, stmt))
        elif isinstance(stmt, ast.ClassDef):
            for item in stmt.body:
                if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef) and item.name.startswith("test"):
                    funcs.append((f"{stmt.name}::{item.name}", item))
    units: list[Unit] = []
    for qual, func in funcs[part::parts]:
        cases, expanded, symbolic, parametrized = parametrize_cases(func, constants)
        params = [a.arg for a in [*func.args.posonlyargs, *func.args.args, *func.args.kwonlyargs]]
        fixtures = [p for p in params if p not in ("self", "cls") and p not in expanded]
        for deco in func.decorator_list:
            if isinstance(deco, ast.Call) and dotted(deco.func).endswith("usefixtures"):
                fixtures += [str(v) for ok, v in map(literal, deco.args) if ok]
        del symbolic  # symbolic names stay ordinary parameters in `fixtures`
        # Fixtures are scoped: one defined in this file, or else in the directory's conftest chain.
        scope = str(Path(path).parent)
        fixture_keys = tuple(sorted(f"{f}@{path if f in local_fixtures else scope}" for f in fixtures))
        base = [collapse(clone(stmt)) for stmt in func.body]
        for label, subst in cases:
            try:
                units.append(
                    py_unit(
                        path,
                        qual,
                        func,
                        base,
                        label,
                        subst,
                        constants,
                        defaults,
                        tuple(fixtures),
                        fixture_keys,
                        parametrized,
                    )
                )
            except RecursionError as error:
                raise ValueError(f"{qual}: too deeply nested") from error
    return units


# ---------------------------------------------------------------- token languages

PUNCT3 = {"===", "!==", "...", "<=>", "**=", "<<=", ">>=", "?->", "??=", "::<"}
PUNCT2 = {
    "->", "=>", "::", "==", "!=", "<=", ">=", "&&", "||", "??", "?.", "+=", "-=", "*=", "/=",
    "%=", "++", "--", "<<", ">>", "..", "|=", "&=", "^=", "**",
}  # fmt: skip
JS_REGEX_PREV = set("(,=:[!&|?{};+-*%<>~^") | {
    "return",
    "typeof",
    "=>",
    "&&",
    "||",
    "??",
    "==",
    "===",
    "!=",
    "!==",
}


RS_RAW = re.compile(r'b?r(#*)"')
RS_CHAR = re.compile(r"'(?:\\.[^']*|[^'\\])'")
RS_LIFETIME = re.compile(r"'\w+")
PHP_HEREDOC = re.compile(r"<<<\s*['\"]?(\w+)['\"]?")
PHP_VAR = re.compile(r"\$\w+")
NUMBER = re.compile(r"0[xXbBoO]\w+|\d[\d_]*(?:\.\d[\d_]*)?(?:[eE][+-]?\d+)?\w*")
IDENT = re.compile(r"[\w$\\]+")
RS_IDENT = re.compile(r"\w+")


@dataclass
class Tok:
    kind: str  # id var num str punct comment
    text: str
    line: int


def tokenize(text: str, lang: str) -> list[Tok]:
    toks: list[Tok] = []
    i, n, line = 0, len(text), 1

    def prev_sig() -> Tok | None:
        for t in reversed(toks):
            if t.kind != "comment":
                return t
        return None

    while i < n:
        c = text[i]
        if c == "\n":
            line += 1
            i += 1
            continue
        if c.isspace():
            i += 1
            continue
        start, start_line = i, line
        two = text[i : i + 2]
        if two == "//" or (lang == "php" and c == "#" and text[i : i + 2] != "#["):
            end = text.find("\n", i)
            end = n if end < 0 else end
            toks.append(Tok("comment", text[i:end], line))
            i = end
            continue
        if two == "/*":
            end = text.find("*/", i + 2)
            end = n if end < 0 else end + 2
            toks.append(Tok("comment", text[i:end], line))
            line += text.count("\n", i, end)
            i = end
            continue
        if lang == "rs" and c in "br" and (m := RS_RAW.match(text, i)):
            closer = '"' + m.group(1)
            end = text.find(closer, m.end())
            end = n if end < 0 else end + len(closer)
            toks.append(Tok("str", text[i:end], line))
            line += text.count("\n", i, end)
            i = end
            continue
        if lang == "php" and text.startswith("<<<", i):
            m = PHP_HEREDOC.match(text, i)
            if m:
                close = re.compile(r"^\s*" + re.escape(m.group(1)) + r"\b", re.MULTILINE)
                found = close.search(text, m.end())
                end = n if found is None else found.end()
                toks.append(Tok("str", text[i:end], line))
                line += text.count("\n", i, end)
                i = end
                continue
        if c == "'" and lang == "rs":
            m = RS_CHAR.match(text, i)
            if m:
                toks.append(Tok("str", m.group(), line))
                line += m.group().count("\n")
                i = m.end()
            else:
                m = RS_LIFETIME.match(text, i)
                toks.append(Tok("id", m.group() if m else "'", line))
                i = m.end() if m else i + 1
            continue
        if c in "\"'" or (c == "`" and lang == "js") or (lang == "rs" and two in ('b"', "b'")):
            quote = text[i + 1] if lang == "rs" and c == "b" else c
            j = i + (2 if lang == "rs" and c == "b" else 1)
            depth = 0
            while j < n:
                ch = text[j]
                if ch == "\\":
                    if text[j + 1 : j + 2] == "\n":  # a Rust/JS line continuation still ends a line
                        line += 1
                    j += 2
                    continue
                if ch == "\n":
                    line += 1
                if quote == "`" and text.startswith("${", j):
                    depth += 1
                    j += 2
                    continue
                if quote == "`" and ch == "}" and depth:
                    depth -= 1
                elif ch == quote and not depth:
                    break
                j += 1
            toks.append(Tok("str", text[i : j + 1], start_line))
            i = j + 1
            continue
        if lang == "js" and c == "/":
            prev = prev_sig()
            if prev is None or prev.text in JS_REGEX_PREV:
                j, in_class, closed = i + 1, False, False
                while j < n and text[j] != "\n":
                    ch = text[j]
                    if ch == "\\":
                        if text[j + 1 : j + 2] == "\n":
                            break
                        j += 2
                        continue
                    if ch == "[":
                        in_class = True
                    elif ch == "]":
                        in_class = False
                    elif ch == "/" and not in_class:
                        closed = True
                        break
                    j += 1
                # A slash with no closer on its line is division or a JSX closing tag (`</div>`).
                if closed:
                    j += 1
                    while j < n and text[j].isalpha():
                        j += 1
                    toks.append(Tok("str", text[i:j], line))
                    i = j
                    continue
        if c.isdigit():
            m = NUMBER.match(text, i)
            assert m is not None
            toks.append(Tok("num", m.group(), line))
            i = m.end()
            continue
        if lang == "php" and c == "$" and i + 1 < n and (text[i + 1].isalpha() or text[i + 1] == "_"):
            m = PHP_VAR.match(text, i)
            assert m is not None
            toks.append(Tok("var", m.group(), line))
            i = m.end()
            continue
        if c.isalpha() or c == "_" or (c == "$" and lang == "js") or (c == "\\" and lang == "php"):
            m = (RS_IDENT if lang == "rs" else IDENT).match(text, i)
            assert m is not None
            toks.append(Tok("id", m.group(), line))
            i = m.end()
            continue
        three = text[i : i + 3]
        if three in PUNCT3:
            toks.append(Tok("punct", three, line))
            i += 3
        elif two in PUNCT2:
            toks.append(Tok("punct", two, line))
            i += 2
        else:
            toks.append(Tok("punct", c, line))
            i += 1
        del start
    return toks


OPEN = {"(": ")", "[": "]", "{": "}"}


def match_close(toks: list[Tok], i: int) -> int:
    depth = 0
    for j in range(i, len(toks)):
        t = toks[j].text if toks[j].kind == "punct" else ""
        if t in OPEN:
            depth += 1
        elif t in (")", "]", "}"):
            depth -= 1
            if depth == 0:
                return j
    return len(toks) - 1


def find_open(toks: list[Tok], i: int, opener: str = "{", stop: str = ";") -> int:
    depth = 0
    for j in range(i, len(toks)):
        t = toks[j].text if toks[j].kind == "punct" else ""
        if t == opener and depth == 0:
            return j
        if t in ("(", "["):
            depth += 1
        elif t in (")", "]"):
            depth -= 1
        elif t == stop and depth == 0:
            return -1
    return -1


def tok_text(toks: list[Tok]) -> str:
    return " ".join(t.text for t in toks)


Found = tuple[str, int, list[Tok], bool, str]


def rust_tests(toks: list[Tok]) -> list[Found]:
    out: list[Found] = []
    i = 0
    while i < len(toks):
        if toks[i].text == "#" and i + 1 < len(toks) and toks[i + 1].text == "[":
            is_test = params = False
            cases: list[str] = []
            j = i
            while j < len(toks) and toks[j].text == "#" and j + 1 < len(toks) and toks[j + 1].text == "[":
                end = match_close(toks, j + 1)
                path = []
                for t in toks[j + 2 : end]:
                    if t.kind == "id" or t.text == "::":
                        path.append(t.text)
                    else:
                        break
                head = "".join(path)
                if head.split("::")[-1] in ("test", "rstest", "test_case") or head == "quickcheck":
                    is_test = True
                    params |= head.split("::")[-1] in ("rstest", "test_case") or "case" in head
                if head in ("case", "test_case", "values") or head.split("::")[-1] == "test_case":
                    params = True
                    cases.append(tok_text(toks[j + 2 : end]))
                j = end + 1
            while j < len(toks) and toks[j].text in ("pub", "async", "unsafe", "const", "(", "crate", ")"):
                j += 1
            if is_test and j + 1 < len(toks) and toks[j].text == "fn":
                name, line = toks[j + 1].text, toks[j + 1].line
                body_open = find_open(toks, j + 2)
                if body_open > 0:
                    close = match_close(toks, body_open)
                    signature = tok_text(toks[j + 2 : body_open])
                    key = f"{signature} {' '.join(cases)}" if params else ""
                    out.append((name, line, toks[body_open + 1 : close], params, key))
                    i = close + 1
                    continue
            i = j if j > i else i + 1
            continue
        i += 1
    return out


def php_tests(toks: list[Tok], raw: list[Tok], path: str) -> list[Found]:
    out: list[Found] = []
    comments_before: dict[int, str] = {}
    sig_index = 0
    for t in raw:
        if t.kind == "comment":
            comments_before[sig_index] = comments_before.get(sig_index, "") + t.text
        else:
            sig_index += 1
    i = 0
    while i < len(toks):
        t = toks[i]
        if t.text == "function" and i + 1 < len(toks) and toks[i + 1].kind == "id":
            name = toks[i + 1].text
            back = toks[max(0, i - 12) : i]
            attr = any(b.text == "Test" for b in back) and any(b.text == "#[" or b.text == "#" for b in back)
            doc = any("@test" in comments_before.get(k, "") for k in range(max(0, i - 6), i + 1))
            if name.startswith("test") or attr or doc:
                body_open = find_open(toks, i + 2)
                if body_open > 0:
                    close = match_close(toks, body_open)
                    params_close = match_close(toks, i + 2) if toks[i + 2].text == "(" else i + 2
                    params = tok_text(toks[i + 3 : params_close])
                    wide = toks[max(0, i - 40) : i]
                    providers = [
                        wide[k + 2].text
                        for k in range(len(wide) - 2)
                        if wide[k].text in ("DataProvider", "TestWith")
                    ]
                    comment = " ".join(comments_before.get(k, "") for k in range(max(0, i - 40), i + 1))
                    providers += re.findall(r"@dataProvider\s+(\w+)", comment)
                    key = f"{path}::{params}::{','.join(providers)}" if params else ""
                    out.append((name, toks[i + 1].line, toks[body_open + 1 : close], bool(params), key))
                    i = close + 1
                    continue
        if (
            t.kind == "id"
            and t.text in ("it", "test")
            and (i == 0 or toks[i - 1].text in (";", "{", "}", ")"))
            and i + 2 < len(toks)
            and toks[i + 1].text == "("
            and toks[i + 2].kind == "str"
        ):
            call_close = match_close(toks, i + 1)
            k = i + 3
            while k < call_close and toks[k].text not in ("function", "fn"):
                k += 1
            if k < call_close:
                arrow = toks[k].text == "fn"
                params_close = match_close(toks, k + 1)
                if arrow:
                    body = toks[params_close + 2 : call_close]
                else:
                    body_open = find_open(toks, params_close + 1)
                    body = toks[body_open + 1 : match_close(toks, body_open)] if body_open > 0 else []
                chained = (
                    call_close + 3 < len(toks)
                    and toks[call_close + 1].text == "->"
                    and toks[call_close + 2].text == "with"
                )
                key = (
                    tok_text(toks[call_close + 3 : match_close(toks, call_close + 3) + 1]) if chained else ""
                )
                out.append(
                    (toks[i + 2].text[1:-1], t.line, body, chained, f"{path}::{key}" if chained else "")
                )
                i = call_close + 1
                continue
        i += 1
    return out


JS_MODIFIERS = {"only", "skip", "concurrent", "sequential", "todo", "fails", "failing", "each"}


def js_tests(toks: list[Tok]) -> list[Found]:
    out: list[Found] = []
    i = 0
    while i < len(toks):
        t = toks[i]
        if (
            t.kind == "id"
            and t.text in ("it", "test")
            and (i == 0 or toks[i - 1].text not in (".", "function"))
        ):
            j, params, table = i + 1, False, ""
            while j + 1 < len(toks) and toks[j].text == "." and toks[j + 1].text in JS_MODIFIERS:
                if toks[j + 1].text == "each":
                    params = True
                    j += 2
                    if j < len(toks) and toks[j].text == "(":
                        close = match_close(toks, j)
                        table = tok_text(toks[j : close + 1])
                        j = close + 1
                    elif j < len(toks) and toks[j].kind == "str":
                        table = toks[j].text
                        j += 1
                    continue
                j += 2
            if j + 1 < len(toks) and toks[j].text == "(" and toks[j + 1].kind == "str":
                call_close = match_close(toks, j)
                k = j + 2
                if k < call_close and toks[k].text == ",":
                    k += 1
                    if toks[k].text == "async":
                        k += 1
                    body: list[Tok] = []
                    if toks[k].text == "function":
                        body_open = find_open(toks, k + 1)
                        if body_open > 0:
                            body = toks[body_open + 1 : match_close(toks, body_open)]
                    else:
                        if toks[k].text == "(":
                            k = match_close(toks, k) + 1
                        else:
                            k += 1
                        if k < call_close and toks[k].text == "=>":
                            k += 1
                            if toks[k].text == "{":
                                body = toks[k + 1 : match_close(toks, k)]
                            else:
                                end = k
                                depth = 0
                                while end < call_close:
                                    x = toks[end].text
                                    if x in OPEN:
                                        depth += 1
                                    elif x in (")", "]", "}"):
                                        depth -= 1
                                    elif x == "," and depth == 0:
                                        break
                                    end += 1
                                body = toks[k:end]
                    if body:
                        out.append((toks[j + 1].text[1:-1], t.line, body, params, table))
                        i = j + 1
                        continue
        i += 1
    return out


CONT = {"else", "catch", "finally", ")", "]", ",", ".", "?.", "->", "?->", ";", "while", "::", "?", ":"}
OPERATORS = set("+-*/%=<>!&|^~?:.,") | PUNCT2 | PUNCT3


def split_statements(body: list[Tok], lang: str) -> list[list[Tok]]:
    stmts: list[list[Tok]] = []
    cur: list[Tok] = []
    depth = 0
    for idx, t in enumerate(body):
        nxt = body[idx + 1] if idx + 1 < len(body) else None
        if t.kind == "punct" and t.text in OPEN:
            depth += 1
        elif t.kind == "punct" and t.text in (")", "]", "}"):
            depth -= 1
        if t.text == ";" and depth == 0 and t.kind == "punct":
            if cur:
                stmts.append(cur)
            cur = []
            continue
        cur.append(t)
        if depth == 0 and nxt is not None and nxt.line > t.line and nxt.text not in CONT:
            block_end = t.text == "}"
            asi = (
                lang == "js" and t.text not in OPERATORS and t.text not in OPEN and nxt.text not in OPERATORS
            )
            if block_end or asi:
                stmts.append(cur)
                cur = []
    if cur:
        stmts.append(cur)
    return stmts


JS_KEYWORDS = {"const", "let", "var"}


def local_names(stmts: list[list[Tok]], lang: str) -> list[str]:
    names: list[str] = []
    for stmt in stmts:
        for idx, t in enumerate(stmt):
            if lang == "php" and t.kind == "var" and t.text != "$this":
                names.append(t.text)
            elif (
                lang in ("js", "rs")
                and t.kind == "id"
                and t.text in (JS_KEYWORDS if lang == "js" else {"let"})
            ):
                depth = 0
                for u in stmt[idx + 1 :]:
                    if u.text in OPEN:
                        depth += 1
                    elif u.text in (")", "]", "}"):
                        depth -= 1
                    if depth <= 0 and u.text in ("=", ";") or (lang == "rs" and depth == 0 and u.text == ":"):
                        break
                    if u.kind == "id" and u.text not in ("mut", "ref", "_") and not u.text[:1].isupper():
                        names.append(u.text)
    return list(dict.fromkeys(names))


PHP_ASSERT = re.compile(
    r"^(?:\$this->|self::|static::|parent::)?(?:assert|expect)\w*\(|^expect\(|^\w*Assert::"
)
JS_ASSERT = re.compile(r"^(?:await )?(?:expect|assert)\b")
RS_ASSERT = re.compile(r"^(?:\w+::)*(?:debug_|prop_)?assert\w*!")


def render(stmt: list[Tok], rename: dict[str, str], abstract: bool) -> str:
    parts = []
    for idx, t in enumerate(stmt):
        text = t.text
        prev = stmt[idx - 1].text if idx else ""
        if t.kind in ("id", "var") and text in rename and prev not in (".", "->", "?.", "::"):
            text = rename[text]
        elif abstract and t.kind in ("str", "num"):
            text = "S" if t.kind == "str" else "N"
        parts.append(text)
    return " ".join(parts)


TOKEN_READERS = re.compile(
    r"^(?:(?:get|query|find)(?:All)?By\w*|within|querySelector(?:All)?|closest|getAttribute|json|count|"
    r"strlen|str_contains|in_array|array_\w+|data_get|isset|is_\w+|len|contains|starts_with|ends_with|"
    r"to_string|to_owned|as_str|as_bytes|unwrap\w*|expect\w*|assert\w*|iter|collect|map|filter|get|keys|"
    r"values|trim|toString|includes|some|every|find|stringify|join|lines|"
    r"sprintf|implode|explode|sort|sorted|toLowerCase|toUpperCase|replace|split|slice|at|Some|Ok|Err|"
    r"String|Number|Boolean|Array|Object|JSON|Math|Date|RegExp|jsonPath|toArray|all|first|"
    r"pluck|fresh|refresh|exists|read\w*|lower|upper|len)$"
)


def embedded_act(stmt: list[Tok]) -> bool:
    """An assertion whose wrapper argument calls something other than a known query or reader."""
    start = next((k for k, t in enumerate(stmt) if t.text == "(" or t.text == "!"), None)
    if start is None:
        return False
    if stmt[start].text == "!":
        start += 1
    if start >= len(stmt) or stmt[start].text != "(":
        return False
    close = match_close(stmt, start)
    for k in range(start + 1, close):
        t = stmt[k]
        if t.kind == "id" and k + 1 < close and stmt[k + 1].text == "(" and not TOKEN_READERS.match(t.text):
            return True
    return False


HTTP_VERBS = ("get", "post", "put", "patch", "delete")


def classify(stmt: list[Tok], lang: str) -> list[tuple[str, list[Tok]]]:
    """Split one statement into (kind, tokens) pieces; PHP ->assert and JS .expect chains split."""
    head = "".join(t.text for t in stmt[:6])
    pattern = {"php": PHP_ASSERT, "js": JS_ASSERT, "rs": RS_ASSERT}[lang]
    if pattern.match(head):
        return [("action", stmt), ("assert", stmt)] if embedded_act(stmt) else [("assert", stmt)]
    arrow, name = ("->", "assert") if lang == "php" else (".", "expect")
    cuts = []
    depth = 0
    for idx, t in enumerate(stmt):
        if t.text in OPEN:
            depth += 1
        elif t.text in (")", "]", "}"):
            depth -= 1
        elif depth == 0 and t.text == arrow and idx + 1 < len(stmt) and stmt[idx + 1].text.startswith(name):
            cuts.append(idx)
    # A JS `.expect(` chain is supertest's only when the prefix builds an HTTP request.
    if (
        lang == "js"
        and cuts
        and not any(t.text in ("request", "supertest", *HTTP_VERBS) for t in stmt[: cuts[0]])
    ):
        cuts = []
    if not cuts:
        return [("action", stmt)]
    pieces: list[tuple[str, list[Tok]]] = []
    prefix = stmt[: cuts[0]]
    if len(prefix) > 1:
        pieces.append(("action", prefix))
    receiver = [Tok("id", "@", 0)] if len(prefix) > 1 else prefix
    for a, b in zip(cuts, [*cuts[1:], len(stmt)], strict=True):
        pieces.append(("assert", receiver + stmt[a:b]))
    return pieces


QUOTES = re.compile(r"""^(?:[bcrf]|br|rb)?#*["'`]|["'`]#*$""")


def token_units(path: str, text: str, lang: str) -> list[Unit]:
    raw = tokenize(text, lang)
    toks = [t for t in raw if t.kind != "comment"]
    if lang == "rs":
        found = rust_tests(toks)
    elif lang == "php":
        found = php_tests(toks, raw, path)
    else:
        found = js_tests(toks)
    shared: set[str] = set()
    if lang == "js":
        inside = {id(t) for _, _, body, _, _ in found for t in body}
        shared = {
            toks[k + 1].text
            for k in range(len(toks) - 1)
            if toks[k].text in ("let", "var") and toks[k + 1].kind == "id" and id(toks[k]) not in inside
        }
    units = []
    for name, line, body, params, key in found:
        # Class state set in setUp()/beforeEach makes an identical body mean different things per file.
        stateful = (
            lang == "php"
            and any(
                t.text == "$this"
                and body[k + 1].text == "->"
                and k + 3 < len(body)
                and body[k + 3].text != "("
                for k, t in enumerate(body[:-2])
            )
        ) or bool(shared and any(t.kind == "id" and t.text in shared for t in body))
        if stateful and not key:
            key = f"{path}::state"
        stmts = split_statements(body, lang)
        pieces = [piece for stmt in stmts for piece in classify(stmt, lang)]
        names = local_names([p for _, p in pieces], lang)
        rename = {n: f"v{i}" for i, n in enumerate(names)}
        kinds = [k for k, _ in pieces]
        last_assert = max((i for i, k in enumerate(kinds) if k == "assert"), default=-1)
        act = max(
            (i for i, k in enumerate(kinds) if k == "action" and (last_assert < 0 or i < last_assert)),
            default=-1,
        )
        actions, shapes, pre, post, ashape = [], [], set(), set(), []
        inputs: set[str] = set()
        needles: set[str] = set()
        real_act = False
        for i, (kind, piece) in enumerate(pieces):
            exact, shape = render(piece, rename, False), render(piece, rename, True)
            bucket = needles if kind == "assert" else inputs
            for t in piece:
                if t.kind == "str":
                    bucket.update(atoms(QUOTES.sub("", t.text)))
            if kind == "assert":
                (pre if i < act else post).add(exact)
                ashape.append(shape)
            else:
                actions.append(exact)
                shapes.append(shape)
                real_act = real_act or any(t.text == "(" for t in piece)
        units.append(
            Unit(
                path=path,
                line=line,
                func=f"{path}::{name}::{line}",
                name=name,
                fixtures=(key,) if key else (),
                actions=tuple(actions),
                action_pos=tuple(actions),
                action_kwargs=(),
                pre=frozenset(pre),
                post=frozenset(post),
                action_shape=tuple(shapes),
                assert_shape=tuple(sorted(ashape)),
                act_shape=render(pieces[act][1], rename, True) if act >= 0 else "",
                setup_shape=tuple(render(p, rename, True) for k, p in pieces[: act + 1] if k == "action"),
                params=params,
                status=status_sig(pre | post),
                inputs=frozenset(inputs),
                needles=frozenset(needles),
                real_act=real_act,
            )
        )
    return units


SCANNERS = {
    ".py": scan_python,
    ".rs": lambda p, t: token_units(p, t, "rs"),
    ".php": lambda p, t: token_units(p, t, "php"),
    **{
        ext: (lambda p, t: token_units(p, t, "js"))
        for ext in (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".mts", ".cts")
    },
}


# ---------------------------------------------------------------- grouping


def superset(a: Unit, b: Unit) -> tuple[Unit, Unit, list[str]] | None:
    """For identical positional calls: (base, superset, extra keywords) when one test only adds keywords."""
    extra_a: list[str] = []
    extra_b: list[str] = []
    for ka, kb in zip(a.action_kwargs, b.action_kwargs, strict=True):
        da, db = dict(ka), dict(kb)
        if any(da[key] != db[key] for key in da.keys() & db.keys()):
            return None
        extra_a += [f"{k}={da[k][:60]}" for k in sorted(da.keys() - db.keys())]
        extra_b += [f"{k}={db[k][:60]}" for k in sorted(db.keys() - da.keys())]
    if extra_a and extra_b or not (extra_a or extra_b):
        return None
    if any(e.startswith("!") for e in extra_a + extra_b):
        return None  # the extra keyword overrides a known default with another value: a different input
    return (b, a, extra_a) if extra_a else (a, b, extra_b)


def trivial(assertion: str) -> bool:
    return bool(STATUS_WORDS.search(assertion)) and assertion.count("==") + assertion.count("!=") == 1


def relate(a: Unit, b: Unit) -> tuple[str, Unit, Unit, str] | None:
    """REDUNDANT / SUBSUMED relation between two same-action units, or None (FOLD territory)."""
    for label, sa, sb in (("", a.full, b.full), ("post", a.post, b.post)):
        if label == "post" and not (a.pre or b.pre):
            break
        note = ""
        if label:
            dropped = [u.name for u in (a, b) if u.pre]
            note = f"; set aside precondition asserts in {', '.join(dropped)}"
        if sa == sb:
            return "REDUNDANT", a, b, note
        if sa < sb:
            return "SUBSUMED", a, b, f"{b.name} adds {len(sb - sa)} assertion(s){note}"
        if sb < sa:
            return "SUBSUMED", b, a, f"{a.name} adds {len(sa - sb)} assertion(s){note}"
    return None


def one_per_func(units: list[Unit]) -> list[Unit]:
    seen: dict[str, Unit] = {}
    for u in units:
        seen.setdefault(u.func, u)
    return list(seen.values())


COMMON_SHARE = 0.5  # a statement shape in more than this share of a file's tests is harness, not signal
SIGNAL_MIN = math.log(4)  # shared-literal IDF that names a contract: one line found in a quarter of the tests
MAX_GROUP = 6
HARNESS_SHARE = 0.7  # with no shared literal, at least this share of statements must be non-harness
MAX_UNMATCHED = 1  # near matches: setup statements only one test runs (a boolean column)


@dataclass
class FileStats:
    """Per-file document frequencies: how many tests carry each statement shape and literal line."""

    tests: int = 0
    shapes: Counter[str] = field(default_factory=Counter)
    atoms: Counter[str] = field(default_factory=Counter)

    def common(self, shape: str) -> bool:
        return self.tests >= 4 and self.shapes[shape] > COMMON_SHARE * self.tests


def file_stats(units: list[Unit]) -> dict[str, FileStats]:
    per_func: dict[str, tuple[str, set[str], set[str]]] = {}
    for u in units:
        _, shapes, found = per_func.setdefault(u.func, (u.path, set(), set()))
        shapes.update(u.action_shape, u.assert_shape)
        found.update(u.inputs, u.needles)
    stats: dict[str, FileStats] = defaultdict(FileStats)
    for path, shapes, found in per_func.values():
        st = stats[path]
        st.tests += 1
        st.shapes.update(shapes)
        st.atoms.update(found)
    return stats


def polarity_flip(a: Unit, b: Unit) -> bool:
    """The assertion shapes differ only by polarity or strength: in/not in, ==/!=, contains/starts_with."""
    only_a = Counter(a.assert_shape) - Counter(b.assert_shape)
    only_b = Counter(b.assert_shape) - Counter(a.assert_shape)
    return any(polar(x) == polar(y) for x in only_a for y in only_b)


def status_conflict(a: Unit, b: Unit) -> bool:
    return bool(a.status and b.status and a.status != b.status)


@dataclass
class Signal:
    inputs: float  # summed IDF of literal lines both tests feed in
    needles: float  # summed IDF of literal lines both tests look for
    informative: int  # shared statement shapes that are not file-wide harness

    @property
    def literal(self) -> float:
        return self.inputs + self.needles

    @property
    def score(self) -> int:
        # Identical distinguishing inputs are the strongest duplicate signal, then shared needles.
        return round(4 * self.inputs + 2 * self.needles) + self.informative

    def describe(self) -> str:
        return f"shared literal weight: inputs {self.inputs:.1f}, needles {self.needles:.1f}"


def signal(a: Unit, b: Unit, st: FileStats) -> Signal:
    def weight(found: frozenset[str]) -> float:
        return sum(math.log((st.tests + 1) / st.atoms[x]) for x in found if st.atoms[x])

    mine = Counter(s for s in a.shape if not st.common(s))
    theirs = Counter(s for s in b.shape if not st.common(s))
    return Signal(weight(a.inputs & b.inputs), weight(a.needles & b.needles), sum((mine & theirs).values()))


def table_pair(a: Unit, b: Unit, st: FileStats, statuses: dict[str, set[frozenset[str]]]) -> Signal | None:
    """Gates every PARAMETRIZE pair; None when the two tests guard different contracts."""
    if a.status != b.status and not (
        a.params and b.status in statuses[a.func] or b.params and a.status in statuses[b.func]
    ):
        return None  # a success row beside a refusal row, unless a table already carries status as a column
    if polarity_flip(a, b):
        return None  # the same check with its polarity or strength flipped
    if a.params and b.params:
        return None  # cases of two parametrized families: each table already names its own contract
    sig = signal(a, b, st)
    if not (a.real_act or b.real_act):
        # Reading a document and slicing a section is the fixture: only the markers say what is pinned.
        return sig if pins_same_markers(a, b, sig) else None
    if sig.literal < SIGNAL_MIN and sig.informative < HARNESS_SHARE * max(len(a.shape), len(b.shape)):
        return None  # the shared shape is mostly file-wide harness and no distinguishing literal is shared
    return sig


def pins_same_markers(a: Unit, b: Unit, sig: Signal) -> bool:
    """Observation-only tests (a document read and sliced) are one contract only when their needles
    overlap: a distinguishing shared needle, covering at least half of the smaller needle set."""
    shared = len(a.needles & b.needles)
    return sig.needles >= SIGNAL_MIN and 2 * shared >= min(len(a.needles), len(b.needles))


def fold_pair(a: Unit, b: Unit, st: FileStats) -> bool:
    if status_conflict(a, b):
        return False
    if not (a.real_act or b.real_act):
        return pins_same_markers(a, b, signal(a, b, st))
    return True


def aligned_setup(a: Unit, b: Unit, ratio: float) -> bool:
    """Setups that differ in statements replaced one for one with the same callee, plus at most one
    statement that only one test runs (a boolean column); two unmatched statements are two inputs."""
    matcher = difflib.SequenceMatcher(None, a.setup_shape, b.setup_shape, autojunk=False)
    unmatched = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag != "replace" or i2 - i1 != j2 - j1:
            unmatched += (i2 - i1) + (j2 - j1)
            continue
        for x, y in zip(a.setup_shape[i1:i2], b.setup_shape[j1:j2], strict=True):
            if head(x) != head(y) and (receiver(x) is None or receiver(x) != receiver(y)):
                return False  # a different callee on a different object: a different fixture
    return unmatched <= MAX_UNMATCHED and matcher.ratio() >= ratio


def cliques(edges: dict[frozenset[str], tuple[int, str]], cap: int) -> list[tuple[list[str], list[str]]]:
    """Groups in which every pair qualifies, strongest pair first; no transitive chaining."""
    adj: dict[str, dict[str, int]] = defaultdict(dict)
    for pair, (score, _) in edges.items():
        x, y = sorted(pair)
        adj[x][y] = adj[y][x] = score
    covered: set[frozenset[str]] = set()
    out = []
    for pair in sorted(edges, key=lambda p: (-edges[p][0], sorted(p))):
        if pair in covered:
            continue
        members = sorted(pair, key=lambda f: f)
        pool = sorted(
            (c for c in adj[members[0]].keys() & adj[members[1]].keys()),
            key=lambda c: (-sum(adj[m][c] for m in members), c),
        )
        extra: list[str] = []
        for c in pool:
            if all(c in adj[m] for m in [*members, *extra]):  # every pair qualifies: no chaining
                (members if len(members) < cap else extra).append(c)
        # The whole family is one finding: its overflow is named, not re-reported as overlapping groups.
        covered.update(frozenset(p) for p in itertools.combinations([*members, *extra], 2))
        out.append((members, extra))
    return out


def family_tail(funcs: list[str], units: dict[str, Unit]) -> str:
    names = [f"{units[f].name}:{units[f].line}" for f in funcs]
    return ", ".join(names[:4]) + (f", +{len(names) - 4} more" if len(names) > 4 else "")


def build_groups(units: list[Unit], ratio: float, cross_file: bool = False) -> list[dict[str, object]]:
    groups: list[dict[str, object]] = []
    paired: set[frozenset[str]] = set()
    stats = file_stats(units)
    statuses: dict[str, set[frozenset[str]]] = defaultdict(set)
    for u in units:
        statuses[u.func].add(u.status)

    def scope(u: Unit) -> str:
        # Identical text in two files usually guards two modules (a per-file import, constant, or setUp).
        return "" if cross_file else u.path

    def emit(
        kind: str,
        match: str,
        reason: str,
        members: list[Unit],
        notes: dict[str, str] | None = None,
        star: bool = False,
        score: int | None = None,
    ) -> None:
        refs = []
        for u in members:
            ref = u.ref()
            if notes and u.name in notes:
                ref["note"] = notes[u.name]
            refs.append(ref)
        group: dict[str, object] = {"kind": kind, "match": match, "reason": reason, "members": refs}
        if score is not None:
            group["score"] = score
        groups.append(group)
        pairs = [(members[0], m) for m in members[1:]] if star else itertools.combinations(members, 2)
        for x, y in pairs:
            paired.add(frozenset((x.func, y.func)))

    def analyze(reps: list[Unit]) -> None:
        """Emit SUBSUMED / FOLD among same-action units whose full assertion sets differ."""
        subsumers: dict[str, list[tuple[Unit, str]]] = defaultdict(list)
        smaller: dict[str, Unit] = {}
        for a, b in itertools.combinations(reps, 2):
            if a.func == b.func or frozenset((a.func, b.func)) in paired or (rel := relate(a, b)) is None:
                continue
            kind, small, big, note = rel
            if kind == "REDUNDANT":
                emit(kind, "exact", "same action and identical result assertions" + note, [a, b])
            else:
                subsumers[small.func].append((big, note))
                smaller[small.func] = small
        for func, bigs in subsumers.items():
            small = smaller[func]
            unique = {big.func: (big, note) for big, note in reversed(bigs)}
            members = [small, *sorted((b for b, _ in unique.values()), key=lambda u: (u.path, u.line))]
            reason = f"same action; every assertion of {small.name} is also asserted by each test below it"
            emit("SUBSUMED", "exact", reason, members, {b.name: n for b, n in unique.values()}, star=True)
        distinct: dict[frozenset[str], Unit] = {}
        for u in reps:
            if u.func not in subsumers:
                distinct.setdefault(u.full, u)
        maximal = {u.func: u for u in one_per_func(list(distinct.values()))}
        edges = {
            frozenset((a.func, b.func)): (len(a.post ^ b.post), "")
            for a, b in itertools.combinations(maximal.values(), 2)
            if fold_pair(a, b, stats[a.path])
        }
        for funcs, extra in cliques(edges, MAX_GROUP):
            members = sorted((maximal[f] for f in funcs), key=lambda u: (u.path, u.line))
            notes = {}
            for u in members:
                others = set().union(*(o.post for o in members if o is not u))
                notes[u.name] = f"{len(u.post - others)} unique assertion(s)"
            reason = "same action, different assertions: fold into one test asserting all of them"
            if extra:
                reason += f" (family capped at {MAX_GROUP}; also: {family_tail(extra, maximal)})"
            emit("FOLD", "exact", reason, members, notes)

    exact: dict[tuple, list[Unit]] = defaultdict(list)
    for u in units:
        if u.actions:
            exact[(scope(u), u.fixtures, u.actions)].append(u)
    for members in exact.values():
        members = one_per_func(members)
        if len(members) < 2:
            continue
        by_full: dict[frozenset[str], list[Unit]] = defaultdict(list)
        for u in members:
            by_full[u.full].append(u)
        reps = []
        for same in by_full.values():
            if len(same) > 1:
                emit("REDUNDANT", "exact", "same action and identical assertions", same)
            reps.append(same[0])
        analyze(reps)

    loose: dict[tuple, list[Unit]] = defaultdict(list)
    for u in units:
        if u.action_kwargs and u.actions:
            loose[(scope(u), u.fixtures, u.action_pos)].append(u)
    for members in loose.values():
        classes: dict[tuple[str, ...], Unit] = {}
        for u in members:
            classes.setdefault(u.actions, u)
        if len(classes) < 2 or len(classes) > 400:
            continue
        for a, b in itertools.combinations(classes.values(), 2):
            if a.func == b.func or frozenset((a.func, b.func)) in paired or (found := superset(a, b)) is None:
                continue
            if a.status != b.status:
                continue
            base, sup, extra = found
            why = f"{sup.name} also passes {', '.join(extra)}"
            rel = relate(base, sup)
            if rel is None:
                continue
            kind, _, big, note = rel
            # Identical (or nested) assertions over an input that differs by keywords: a table row,
            # or a duplicate only when the extra values are the callee's defaults.
            relation = "identical assertions" if kind == "REDUNDANT" else f"{big.name} asserts a superset"
            reason = (
                f"same calls, {relation}{note}; {why}: one table row per input, "
                "or redundant if those are the callee's defaults"
            )
            emit("PARAMETRIZE", "kwarg-superset", reason, [base, sup])

    edges: dict[frozenset[str], tuple[int, str]] = {}
    edge_cases: dict[frozenset[str], tuple[str, str]] = {}

    def link(a: Unit, b: Unit, why: str) -> None:
        pair = frozenset((a.func, b.func))
        if a.func == b.func or a.actions == b.actions or pair in paired:
            return
        sig = table_pair(a, b, stats[a.path], statuses)
        if sig is None:
            return
        if pair not in edges or sig.score > edges[pair][0]:
            edges[pair] = (sig.score, f"{why}; {sig.describe()}")
            edge_cases[pair] = (a.name, b.name)

    def link_bucket(bucket: dict[tuple, list[Unit]], why: str, check=None) -> None:
        for members in bucket.values():
            if len({u.func for u in members}) < 2 or len(members) > 400:
                continue
            for a, b in itertools.combinations(members, 2):
                if a.func != b.func and (check is None or check(a, b)):
                    link(a, b, why)

    full_shape: dict[tuple, list[Unit]] = defaultdict(list)
    act_shape: dict[tuple, list[Unit]] = defaultdict(list)
    near: dict[tuple, list[Unit]] = defaultdict(list)
    for u in units:
        if len(u.action_shape) + len(u.assert_shape) < 2:
            continue
        full_shape[(scope(u), u.fixtures, u.action_shape, u.assert_shape)].append(u)
        if u.assert_shape:
            act_shape[(scope(u), u.fixtures, u.action_shape)].append(u)
        if u.post and any(not trivial(a) for a in u.post) and u.setup_shape:
            # The expected status is compared by the gate (a table may already carry it as a column).
            result = frozenset(STATUS_INT.sub("N", a) if trivial(a) else a for a in u.post)
            near[(u.path, u.fixtures, result, u.act_shape)].append(u)

    def shape_close(a: Unit, b: Unit) -> bool:
        # One test checks one more observable, or the same observable with another needle shape;
        # an assertion replaced by one on another observable is a different contract.
        only_a = Counter(a.assert_shape) - Counter(b.assert_shape)
        only_b = Counter(b.assert_shape) - Counter(a.assert_shape)
        sizes = sorted((sum(only_a.values()), sum(only_b.values())))
        if sizes == [0, 1]:
            return True
        return sizes == [1, 1] and subject(next(iter(only_a))) == subject(next(iter(only_b)))

    link_bucket(full_shape, "identical structure once literals are abstracted")
    link_bucket(act_shape, "same action shape; assertion shapes differ by one entry", shape_close)
    link_bucket(
        near,
        f"identical result assertions over setup at least {ratio:.0%} similar, differing only in arguments",
        lambda a, b: aligned_setup(a, b, ratio),
    )

    first: dict[str, Unit] = {}
    for u in units:
        first.setdefault(u.func, u)
    for funcs, extra in cliques(edges, MAX_GROUP):
        members = [first[f] for f in funcs]
        pairs = [p for p in itertools.combinations(funcs, 2) if frozenset(p) in edges]
        top = max(pairs, key=lambda p: edges[frozenset(p)][0])
        score = edges[frozenset(top)][0]
        reason = edges[frozenset(top)][1]
        if extra:
            reason += f" (family capped at {MAX_GROUP}; also: {family_tail(extra, first)})"
        notes: dict[str, str] = {}
        for pair in pairs:
            for case in edge_cases[frozenset(pair)]:
                if "[" in case:
                    base = case.split("[", 1)[0]
                    for u in members:
                        if u.name.split("[", 1)[0] == base:
                            notes[u.name] = f"parametrized; matched case {case[len(base) :]}"
        emit("PARAMETRIZE", "shape", reason, members, notes, score=score)
    return groups


def scan_job(job: tuple[str, int, int]) -> tuple[list[Unit], str | None]:
    path, part, parts = job
    try:
        text = Path(path).read_text(errors="replace")
        if path.endswith(".py"):
            return scan_python(path, text, part, parts), None
        return SCANNERS[Path(path).suffix](path, text), None
    except (OSError, SyntaxError, ValueError, RecursionError) as error:
        return [], str(error)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("patterns", nargs="+", help="globs of test files (** allowed)")
    parser.add_argument("--kind", action="append", help="only report these kinds")
    parser.add_argument("--json", action="store_true", help="write JSON to stdout")
    parser.add_argument(
        "--explain",
        metavar="SUBSTR",
        help="print the normalized signature of tests whose name contains SUBSTR",
    )
    parser.add_argument(
        "--cross-file",
        action="store_true",
        help="also pair tests from different files (copy-paste hunting; bodies may name different modules)",
    )
    parser.add_argument(
        "--jobs", type=int, default=os.cpu_count() or 1, help="worker processes (default: all cores)"
    )
    parser.add_argument(
        "--ratio",
        type=float,
        default=0.75,
        help="setup similarity for PARAMETRIZE near matches (default 0.75)",
    )
    args = parser.parse_args()

    pattern_files = [(pattern, expand([pattern])) for pattern in args.patterns]
    matched = sorted({name for _, names in pattern_files for name in names})
    unmatched = [pattern for pattern, names in pattern_files if not names]
    for pattern in unmatched:
        print(f"duplicate_tests: unmatched pattern (no eligible files): {pattern}", file=sys.stderr)
    files = [f for f in matched if Path(f).suffix in SCANNERS]
    unsupported = [f for f in matched if Path(f).suffix not in SCANNERS]
    if not files:
        print("duplicate_tests: no supported files matched; audit input is incomplete", file=sys.stderr)
    jobs = []
    errors: dict[str, str] = {}
    for name in files:
        try:
            parts = 1 + Path(name).stat().st_size // 100_000 if name.endswith(".py") else 1
        except OSError as error:
            errors[name] = str(error)
            continue
        jobs += [(name, part, parts) for part in range(parts)]
    units: list[Unit] = []
    if args.jobs > 1 and len(jobs) > 1:
        with ProcessPoolExecutor(max_workers=min(args.jobs, len(jobs))) as pool:
            for job, (found, error) in zip(jobs, pool.map(scan_job, jobs), strict=True):
                units.extend(found)
                if error is not None:
                    errors[job[0]] = error
    else:
        for job in jobs:
            found, error = scan_job(job)
            units.extend(found)
            if error is not None:
                errors[job[0]] = error
    units.sort(key=lambda u: (u.path, u.line))
    recognized = {u.path for u in units}
    unrecognized = sorted(set(files) - recognized - errors.keys())
    input_complete = bool(files) and not (unmatched or unsupported or errors or unrecognized)
    for name in unsupported:
        print(f"duplicate_tests: unsupported file: {name}", file=sys.stderr)
    for name, error in sorted(errors.items()):
        print(f"duplicate_tests: unparsed {name}: {error}", file=sys.stderr)
    for name in unrecognized:
        print(
            f"duplicate_tests: no recognized tests in {name}; helper file or unsupported test syntax",
            file=sys.stderr,
        )
    if args.explain:
        for u in units:
            if args.explain in u.name:
                print(f"{u.path}:{u.line}  {u.name}  fixtures={list(u.fixtures)}")
                for text in u.actions:
                    print(f"  act     {text}")
                for label, bucket in (("pre", u.pre), ("assert", u.post)):
                    for text in sorted(bucket):
                        print(f"  {label:<7} {text}")
                print(f"  final   {u.act_shape}\n")
        return 0 if input_complete else 2
    groups = build_groups(units, args.ratio, args.cross_file)
    if args.kind:
        groups = [g for g in groups if g["kind"] in args.kind]
    order = {"REDUNDANT": 0, "SUBSUMED": 1, "FOLD": 2, "PARAMETRIZE": 3}
    groups.sort(
        key=lambda g: (
            order[g["kind"]],  # type: ignore[index]
            g["members"][0]["file"],  # type: ignore[index]
            -g.get("score", 0),  # type: ignore[operator]
            g["members"][0]["line"],  # type: ignore[index]
        )
    )
    counts = Counter(g["kind"] for g in groups)
    tests = len({u.func for u in units})
    if args.json:
        json.dump(
            {
                "files": len(files),
                "tests": tests,
                "units": len(units),
                "input_complete": input_complete,
                "unmatched_patterns": unmatched,
                "unsupported_files": unsupported,
                "unparsed_files": [{"file": name, "error": error} for name, error in sorted(errors.items())],
                "unrecognized_files": unrecognized,
                "counts": dict(counts),
                "groups": groups,
            },
            sys.stdout,
            indent=1,
        )
        print()
    else:
        for g in groups:
            print(f"{g['kind']} [{g['match']}] {g['reason']}")
            for m in g["members"]:  # type: ignore[attr-defined]
                note = f"  ({m['note']})" if "note" in m else ""
                print(f"  {m['file']}:{m['line']}  {m['test']}{note}")
            print()
    summary = ", ".join(f"{k} {counts[k]}" for k in order if counts[k]) or "none"
    print(f"{len(files)} files, {tests} tests ({len(units)} cases); groups: {summary}", file=sys.stderr)
    return 0 if input_complete else 2


if __name__ == "__main__":
    sys.exit(main())
