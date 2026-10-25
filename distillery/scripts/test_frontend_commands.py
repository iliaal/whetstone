import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest


ROOT = Path(__file__).resolve().parents[2]
COMMANDS = ROOT / "plugins/whetstone/commands"
PORT_HELPER = COMMANDS / "scripts/resolve-dev-port"
VIDEO_COMMAND = COMMANDS / "ia-feature-video.md"


def resolve_port(directory, argument=None):
    command = ["bash", str(PORT_HELPER)]
    if argument is not None:
        command.append(argument)
    result = subprocess.run(command, cwd=directory, capture_output=True, text=True, check=True)
    assert result.stderr == ""
    return result.stdout.strip()


@pytest.mark.parametrize(
    ("dependencies", "expected"),
    [
        ({"astro": "*"}, "4321"),
        ({"nuxt": "*"}, "3000"),
        ({"vite": "*"}, "5173"),
        ({"@sveltejs/kit": "*"}, "5173"),
        ({"next": "*"}, "3000"),
        ({"astro": "*", "vite": "*"}, "4321"),
        ({"nuxt": "*", "vite": "*"}, "3000"),
        ({}, "3000"),
    ],
)
def test_framework_port_defaults(tmp_path, dependencies, expected):
    (tmp_path / "package.json").write_text(json.dumps({"devDependencies": dependencies}))
    assert resolve_port(tmp_path) == expected


def test_explicit_and_configured_ports_override_framework_defaults(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({
        "devDependencies": {"astro": "*"},
        "scripts": {"dev": "astro dev --port 4567"},
    }))
    (tmp_path / ".env").write_text("PORT=6789\n")
    assert resolve_port(tmp_path, "01234") == "1234"
    assert resolve_port(tmp_path) == "4567"
    (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"astro": "*"}}))
    assert resolve_port(tmp_path) == "6789"


def test_video_port_lookup_supports_plugin_paths_with_spaces(tmp_path):
    plugin_root = tmp_path / "plugin with spaces"
    target = plugin_root / "commands/scripts/resolve-dev-port"
    target.parent.mkdir(parents=True)
    shutil.copyfile(PORT_HELPER, target)
    (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"astro": "*"}}))
    invocation = next(
        line.strip() for line in VIDEO_COMMAND.read_text().splitlines()
        if "echo" in line and "commands/scripts/resolve-dev-port" in line
    )
    result = subprocess.run(
        ["bash", "-c", invocation], cwd=tmp_path, capture_output=True, text=True,
        env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(plugin_root)},
    )
    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout.strip() == "http://localhost:4321"


def public_url_gate():
    match = re.search(r'^PREVIEW_URL=.*?\n(.*?)\n```', VIDEO_COMMAND.read_text(), re.M | re.S)
    assert match is not None
    return match.group(1)


def run_public_url_gate(video_url, preview_url, proxy=None):
    env = {key: value for key, value in os.environ.items() if not key.lower().endswith("_proxy")}
    env.update(VIDEO_URL=video_url, PREVIEW_URL=preview_url, NO_PROXY="*")
    if proxy:
        env.update(HTTPS_PROXY=proxy, NO_PROXY="")
    return subprocess.run(
        ["bash", "-c", public_url_gate()], env=env, capture_output=True, text=True, timeout=10,
    )


@pytest.mark.parametrize(
    ("video_status", "preview_status", "accepted", "requests_expected"),
    [
        (200, 200, True, ["/video", "/preview"]),
        (404, 200, False, ["/video"]),
        (200, 404, False, ["/video", "/preview"]),
        (302, 200, False, ["/video"]),
        (200, 302, False, ["/video", "/preview"]),
    ],
)
def test_video_requires_direct_success_for_both_urls(
    video_status, preview_status, accepted, requests_expected,
):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_HEAD(self):
            requests.append(self.path)
            self.send_response({"/video": video_status, "/preview": preview_status}[self.path])
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        result = run_public_url_gate(f"{base}/video", f"{base}/preview")
        assert (result.returncode == 0) is accepted, result.stderr
        assert requests == requests_expected
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    assert not thread.is_alive()


def test_proxy_connect_success_does_not_hide_tls_failure():
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    listener.settimeout(0.1)
    proxy = f"http://127.0.0.1:{listener.getsockname()[1]}"
    requests = []
    stopped = threading.Event()

    def answer_connect():
        try:
            while not stopped.is_set():
                try:
                    conn, _ = listener.accept()
                except TimeoutError:
                    continue
                with conn:
                    requests.append(conn.recv(8192))
                    conn.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
        finally:
            listener.close()

    thread = threading.Thread(target=answer_connect)
    thread.start()
    try:
        result = run_public_url_gate(
            "https://unreachable.invalid/video", "https://unreachable.invalid/preview", proxy,
        )
    finally:
        stopped.set()
        thread.join(timeout=2)
    assert not thread.is_alive()
    assert len(requests) == 1
    assert requests[0].startswith(b"CONNECT unreachable.invalid:443 ")
    assert result.returncode != 0
    assert "curl:" in result.stderr
