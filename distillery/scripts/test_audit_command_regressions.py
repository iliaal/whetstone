"""Exercise the real feedback helper with a mock gh; no network or posting."""

import json
import os
from pathlib import Path
import subprocess

import pytest


HELPER = Path(__file__).resolve().parents[2] / "plugins/whetstone/commands/scripts/get-pr-comments"


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
        ["bash", str(HELPER), *args], text=True, capture_output=True,
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


def comment(identifier, body="feedback", author="reviewer"):
    return {"id": identifier, "body": body, "author": {"login": author},
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
