"""Exercise the real feedback helper with a mock gh; no network or posting."""

import json
import os
from pathlib import Path
import re
import subprocess

import pytest


HELPER = Path(__file__).resolve().parents[2] / "plugins/whetstone/commands/scripts/get-pr-comments"


@pytest.mark.parametrize("exit_code", [0, 1])
@pytest.mark.parametrize("document", [
    "agents/ia-pr-comment-resolver.md",
    "skills/ia-receiving-code-review/references/fix-and-handoff.md",
])
def test_review_reply_example_preserves_thread_body_and_exit_status(tmp_path, exit_code, document):
    source = HELPER.parents[2] / document
    section = source.read_text().split("Draft", 1)[1]
    example = re.search(r"```bash\n(.*?)```", section, re.S)
    assert example, "Review-thread reply must provide an executable example"
    body = 'Fixed `path` with "quotes".\n$(touch unexpected) ${HOME} \\n\n'
    reply = tmp_path / "approved reply.md"
    reply.write_text(body)
    capture = tmp_path / "request.json"
    mock = tmp_path / "gh"
    mock.write_text("""#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
assert args[0] == 'api', args
fields = {}
for flag, field in zip(args[2::2], args[3::2]):
    key, value = field.split('=', 1)
    if flag == '-F' and value.startswith('@'):
        value = Path(value[1:]).read_text()
    else:
        assert flag == '-f', flag
    fields[key] = value
Path(os.environ['CAPTURE']).write_text(json.dumps({'endpoint': args[1], 'fields': fields}))
sys.exit(int(os.environ['EXIT_CODE']))
""")
    mock.chmod(0o755)
    result = subprocess.run(
        ["bash", "-c", example.group(1)], cwd=tmp_path, text=True, capture_output=True,
        env={**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}",
             "THREAD_ID": "PRRT_opaque-thread-id", "REPLY_FILE": str(reply),
             "PR_NUMBER": "123", "COMMENT_ID": "456",
             "CAPTURE": str(capture), "EXIT_CODE": str(exit_code)},
    )
    assert result.returncode == exit_code, result.stderr
    request = json.loads(capture.read_text())
    fields = request["fields"]
    assert fields["body"] == body
    if document.startswith("agents/"):
        assert request["endpoint"] == "graphql"
        assert fields["thread"] == "PRRT_opaque-thread-id"
        assert "pullRequestReviewThreadId: $thread" in fields["query"]
        assert "body: $body" in fields["query"]
        assert "addPullRequestReviewThreadReply" in fields["query"]
    else:
        assert request["endpoint"] == "repos/{owner}/{repo}/pulls/123/comments/456/replies"
        assert set(fields) == {"body"}
    assert not (tmp_path / "unexpected").exists()


def run_mock(tmp_path, responses, args=("123", "owner/repo")):
    fixture = tmp_path / "responses.json"
    fixture.write_text(json.dumps(responses))
    mock = tmp_path / "gh"
    mock.write_text("""#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
path = Path(os.environ['MOCK_GH_RESPONSES'])
responses = json.loads(path.read_text())
if not responses:
    sys.exit('Unexpected mock gh call: ' + repr(sys.argv))
response = responses.pop(0)
path.write_text(json.dumps(responses))
for expected in response.get('args', []):
    if not any(expected in arg for arg in sys.argv):
        sys.exit('Missing expected argument: ' + expected)
print(json.dumps(response.get('json', {})))
if response.get('stderr'):
    print(response['stderr'], file=sys.stderr)
sys.exit(response.get('exit', 0))
""")
    mock.chmod(0o755)
    result = subprocess.run(
        ["python3", str(HELPER), *args], text=True, capture_output=True,
        env={**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}",
             "MOCK_GH_RESPONSES": str(fixture)},
    )
    return result, json.loads(fixture.read_text())


def metadata():
    return {"args": ["FeedbackMetadata", "owner=owner", "repo=repo", "pr=123"],
            "json": {"data": {"repository": {"pullRequest": {"author": {"login": "author"}}}}}}


def page(name, nodes, cursor=None, next_cursor=None, thread=None):
    connection = {"nodes": nodes, "pageInfo": {
        "hasNextPage": next_cursor is not None, "endCursor": next_cursor}}
    data = ({"node": {"comments": connection}} if thread else
            {"repository": {"pullRequest": {name: connection}}})
    args = ["ThreadComments", f"thread={thread}"] if thread else [name + "(first: 100"]
    if cursor:
        args.append("cursor=" + cursor)
    return {"args": args, "json": {"data": data}}


def comment(identifier, body="feedback", author="reviewer", association="MEMBER", kind="User"):
    return {"id": identifier, "body": body, "author": {"login": author, "__typename": kind},
            "authorAssociation": association,
            "createdAt": "2026-09-07", "url": "https://example.invalid/comment"}


def thread(identifier, resolved=False, outdated=False):
    return {"id": identifier, "isResolved": resolved, "isOutdated": outdated,
            "path": "app.py", "line": 4, "comments": {"nodes": [], "totalCount": 0,
            "pageInfo": {"hasNextPage": False, "endCursor": None}}}


def test_mock_paginates_all_four_connections_and_preserves_contract(tmp_path):
    comments = [comment(str(i)) for i in range(100)]
    reviews = [{**comment(str(i)), "state": "COMMENTED"} for i in range(100)]
    threads = [thread(str(i)) for i in range(100)]
    threads[0]["comments"] = {"nodes": comments, "totalCount": 101,
                              "pageInfo": {"hasNextPage": True, "endCursor": "tc"}}
    responses = [metadata(),
                 page("comments", comments, next_cursor="c"),
                 page("comments", [comment("last", author="author"), comment("blank", " \n")], cursor="c"),
                 page("reviews", reviews, next_cursor="r"),
                 page("reviews", [comment("last-review")], cursor="r"),
                 page("reviewThreads", threads, next_cursor="t"),
                 page("reviewThreads", [thread("resolved", resolved=True), thread("old", outdated=True)], cursor="t"),
                 page("comments", [comment("last-thread-comment")], cursor="tc", thread="0")]
    result, remaining = run_mock(tmp_path, responses)
    assert result.returncode == 0, result.stderr
    assert not remaining
    output = json.loads(result.stdout)
    assert len(output["conversation"]["comments"]) == 101
    assert output["conversation"]["comments"][-1]["by_pr_author"] is True
    assert len(output["conversation"]["review_bodies"]) == 101
    assert len(output["unresolved"]) == 100
    assert output["unresolved"][0]["node"]["comments"]["nodes"][-1]["id"] == "last-thread-comment"
    assert output["cross_invocation"] == {"signal": True, "resolved_threads": [
        {"node": {"id": "resolved", "path": "app.py", "line": 4}}]}


@pytest.mark.parametrize("failure", [
    {"exit": 17, "stderr": "mock transport failure"},
    {"json": {"errors": [{"message": "mock permission denied"}]}},
    {"json": {"data": None}},
])
def test_mock_failure_never_returns_partial_success(tmp_path, failure):
    result, remaining = run_mock(tmp_path, [metadata(), page("comments", []), failure])
    assert result.returncode != 0
    assert result.stdout == ""
    assert "Error fetching PR feedback" in result.stderr
    assert not remaining


def test_mock_repeated_cursor_fails_closed(tmp_path):
    result, _ = run_mock(tmp_path, [metadata(), page("comments", [], next_cursor="same"),
                                  page("comments", [], cursor="same", next_cursor="same")])
    assert result.returncode != 0
    assert result.stdout == ""
    assert "Pagination did not advance" in result.stderr


def test_mock_trust_derives_from_association_bot_type_and_allowlist(tmp_path, monkeypatch):
    monkeypatch.setenv("PR_COMMENT_TRUSTED_LOGINS", " Allowed-User , coderabbitai[bot]")
    comments = [comment("owner", association="OWNER"),
                comment("member", association="MEMBER"),
                comment("collab", association="COLLABORATOR"),
                comment("contrib", association="CONTRIBUTOR"),
                comment("first", association="FIRST_TIME_CONTRIBUTOR"),
                comment("none", association="NONE"),
                comment("missing", association=None),
                comment("bot", author="dependabot", association="MEMBER", kind="Bot"),
                comment("allowed-bot", author="coderabbitai", association="NONE", kind="Bot"),
                comment("allowed-user", author="allowed-user", association="NONE"),
                {**comment("ghost"), "author": None}]
    mixed = thread("mixed")
    mixed["comments"]["nodes"] = [comment("t1"), comment("t2", association="NONE")]
    clean = thread("clean")
    clean["comments"]["nodes"] = [comment("t3", association="OWNER")]
    feedback = [page("comments", comments), page("reviews", []),
                page("reviewThreads", [mixed, clean, thread("empty")])]
    for response in feedback:
        response["args"].append("author { login __typename } authorAssociation")
    result, remaining = run_mock(tmp_path, [metadata(), *feedback])
    assert result.returncode == 0, result.stderr
    assert not remaining
    output = json.loads(result.stdout)
    trust = {item["id"]: item["trusted"] for item in output["conversation"]["comments"]}
    assert trust == {"owner": True, "member": True, "collab": True, "contrib": False,
                     "first": False, "none": False, "missing": False, "bot": False,
                     "allowed-bot": True, "allowed-user": True, "ghost": False}
    by_id = {item["id"]: item for item in output["conversation"]["comments"]}
    assert by_id["bot"]["author_is_bot"] is True
    assert by_id["contrib"]["author_association"] == "CONTRIBUTOR"
    assert by_id["missing"]["author_association"] == "NONE"
    threads = {item["node"]["id"]: item["node"] for item in output["unresolved"]}
    assert threads["mixed"]["trusted"] is False
    assert [c["trusted"] for c in threads["mixed"]["comments"]["nodes"]] == [True, False]
    assert threads["clean"]["trusted"] is True
    assert threads["empty"]["trusted"] is False


def test_mock_repository_detection_and_empty_feedback(tmp_path):
    result, remaining = run_mock(tmp_path, [
        {"args": ["repo", "view", "owner,name"], "json": {"owner": {"login": "owner"}, "name": "repo"}},
        metadata(), page("comments", []), page("reviews", []), page("reviewThreads", [])], args=("123",))
    assert result.returncode == 0, result.stderr
    assert not remaining
    output = json.loads(result.stdout)
    assert output["unresolved"] == []
    assert output["conversation"]["comments"] == []
    assert output["cross_invocation"]["signal"] is False


def test_resolve_pr_approval_view_shows_staged_unstaged_and_new_files(tmp_path):
    doc = (HELPER.parents[1] / "ia-resolve-pr.md").read_text()
    phase = doc.split("## Phase 4", 1)[1]
    view = re.search(r"```bash\n(.*?)```", phase, re.S)
    assert view, "Phase 4 must prescribe an executable approval view"
    assert re.search(r"git commit -m [^`]*-- <approved paths>", phase)
    assert "git commit -a" in phase and "git add -A" in phase

    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}

    def git(*args):
        return subprocess.run(["git", *args], cwd=tmp_path, env=env, text=True,
                              capture_output=True, check=True)

    git("init", "-q")
    (tmp_path / "staged.txt").write_text("base\n")
    (tmp_path / "unstaged.txt").write_text("base\n")
    git("add", ".")
    git("commit", "-qm", "base")
    (tmp_path / "staged.txt").write_text("STAGED_CHANGE\n")
    git("add", "staged.txt")
    (tmp_path / "unstaged.txt").write_text("UNSTAGED_CHANGE\n")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "new file.txt").write_text("NEW_FILE_CONTENT\n")

    result = subprocess.run(["bash", "-c", view.group(1)], cwd=tmp_path, env=env,
                            text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    for marker in ("+STAGED_CHANGE", "+UNSTAGED_CHANGE", "+NEW_FILE_CONTENT", "sub/new file.txt"):
        assert marker in result.stdout, marker

    git("commit", "-qm", "address review: x", "--", "staged.txt", "sub/new file.txt")
    committed = git("diff", "--name-only", "HEAD~1", "HEAD").stdout.split("\n")
    assert sorted(filter(None, committed)) == ["staged.txt", "sub/new file.txt"]
