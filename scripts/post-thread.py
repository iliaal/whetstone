#!/usr/bin/env python3
"""Compose a thread on X (Twitter) via the compound-engineering Edge profile.

Drafts the thread only -- the user clicks Post manually in the browser.

Prerequisites:
    1. Auto-launches the compound-engineering Edge profile if not already running
       (via edge-cdp ensure compound-engineering). First run: log in to X manually.
    2. Provide a JSON file containing the thread.

JSON schema (backwards compatible):
    Either a flat array of strings:
        ["post 1 text", "post 2 text", "post 3 text"]

    Or an array of {text, images?} objects (mix freely with strings):
        [
            {"text": "post 1 text"},
            {"text": "post 2 text", "images": ["diagram.png"]},
            {"text": "post 3 text", "image": "~/path/to/single.jpg"}
        ]

    Image rules:
        - Relative paths resolve against the JSON file's directory.
        - "~" expands to $HOME.
        - "image" (singular) is shorthand for images=[that_path].
        - X limits each post to 4 attachments.
        - File must exist at load time (validated before browser launch).

Usage:
    python3 scripts/post-thread.py tweets.json

Environment:
    EDGE_PROFILE  Override profile name (default: compound-engineering)
"""

import json
import os
import sys
import time

from edge_cdp import connect
from playwright.sync_api import TimeoutError as PwTimeout

PROFILE = os.environ.get("EDGE_PROFILE", "compound-engineering")
COMPOSE_URL = "https://x.com/compose/post"
MAX_TWEET_LEN = 25000  # X Premium / Pro limit; free accounts get 280.
MAX_IMAGES_PER_TWEET = 4  # X limit.


def die(msg: str) -> None:
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


def load_tweets(source: str) -> list[dict]:
    """Read JSON and normalize to [{text, images: [abs_path]}, ...]."""
    with open(source) as f:
        data = json.load(f)

    if not isinstance(data, list):
        die("input must be a JSON array")

    base_dir = os.path.dirname(os.path.abspath(source))
    normalized: list[dict] = []

    for i, item in enumerate(data, start=1):
        if isinstance(item, str):
            text = item
            raw_images: list[str] = []
        elif isinstance(item, dict):
            text = item.get("text")
            if not isinstance(text, str):
                die(f"tweet {i} object must have a 'text' string field")
            raw_images = []
            if "image" in item:
                if not isinstance(item["image"], str):
                    die(f"tweet {i} 'image' must be a string path")
                raw_images.append(item["image"])
            if "images" in item:
                if not isinstance(item["images"], list) or not all(
                    isinstance(p, str) for p in item["images"]
                ):
                    die(f"tweet {i} 'images' must be a list of string paths")
                raw_images.extend(item["images"])
        else:
            die(
                f"tweet {i} must be a string or an object with 'text' and "
                f"optional 'image'/'images' fields"
            )

        if len(text) > MAX_TWEET_LEN:
            die(f"tweet {i} is {len(text)} chars (max {MAX_TWEET_LEN})")
        if len(raw_images) > MAX_IMAGES_PER_TWEET:
            die(
                f"tweet {i} has {len(raw_images)} images "
                f"(X max is {MAX_IMAGES_PER_TWEET} per post)"
            )

        resolved_images: list[str] = []
        for p in raw_images:
            full = os.path.expanduser(p)
            if not os.path.isabs(full):
                full = os.path.join(base_dir, full)
            full = os.path.normpath(full)
            if not os.path.isfile(full):
                die(f"tweet {i} image not found: {full}")
            resolved_images.append(full)

        normalized.append({"text": text, "images": resolved_images})

    return normalized


def check_login(page) -> bool:
    page.goto("https://x.com/home", wait_until="domcontentloaded")
    time.sleep(3)

    if "login" in page.url.lower() or "i/flow" in page.url.lower():
        return False

    try:
        page.locator('[data-testid="SideNav_AccountSwitcher_Button"]').first.wait_for(timeout=10000)
        return True
    except PwTimeout:
        try:
            page.locator('[data-testid="AppTabBar_Home_Link"]').first.wait_for(timeout=5000)
            return True
        except PwTimeout:
            return False


def attach_images(page, tweet_idx: int, image_paths: list[str]) -> None:
    """Upload images to the tweet box at `tweet_idx`.

    X's thread compose renders multiple `[data-testid="fileInput"]` nodes but
    uploads route to the currently *focused* tweet, not to the input element
    you call `set_input_files` on. Index- and ancestor-scoped lookups both
    misattach in multi-tweet threads (verified empirically against a 3-post
    compose). The reliable pattern: click the target tweet's textarea to
    focus it, then drive `set_input_files` against any fileInput in the DOM.
    """
    if not image_paths:
        return

    editor = page.locator(f'[data-testid="tweetTextarea_{tweet_idx}"]').first
    editor.click()
    time.sleep(0.5)

    file_input = page.locator('input[data-testid="fileInput"]').first
    if file_input.count() == 0:
        print(f"      WARN: no fileInput found in compose; tweet {tweet_idx + 1} image skipped")
        return

    file_input.set_input_files(image_paths)

    # Wait for X to render the attachment thumbnail. The selector for the
    # thumbnail container drifts between X releases; a fixed sleep is generous
    # enough for typical promo images (under a few MB). Bump if X warns "still
    # uploading" on submit.
    time.sleep(2)
    print(f"      attached {len(image_paths)} image(s)")


def compose_thread(tweets: list[dict], profile: str):
    pw, browser, context, page = connect(profile)

    if not check_login(page):
        print("Not logged in. Opening login page.")
        page.goto("https://x.com/login", wait_until="domcontentloaded")
        print("Log in to X, then re-run the script.")
        pw.stop()
        sys.exit(1)

    print("Logged in. Opening compose dialog...")
    page.goto(COMPOSE_URL, wait_until="domcontentloaded")
    time.sleep(3)

    for idx, item in enumerate(tweets):
        textarea_id = f"tweetTextarea_{idx}"
        editor = page.locator(f'[data-testid="{textarea_id}"]').first
        editor.wait_for(timeout=10000)
        editor.click()
        time.sleep(0.5)

        lines = item["text"].split("\n")
        for i, line in enumerate(lines):
            page.keyboard.type(line, delay=12)
            if i < len(lines) - 1:
                page.keyboard.press("Enter")

        print(f"  [{idx + 1}/{len(tweets)}] Typed ({len(item['text'])} chars)")

        if item["images"]:
            attach_images(page, idx, item["images"])

        if idx < len(tweets) - 1:
            time.sleep(0.5)
            add_btn = page.locator('[data-testid="addButton"]').first
            add_btn.wait_for(timeout=5000)
            add_btn.click()
            time.sleep(1)

    print(f"\nAll {len(tweets)} tweets composed. Review in browser and click Post when ready.")
    pw.stop()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if not args:
        print(f"Usage: {sys.argv[0]} <tweets.json>", file=sys.stderr)
        sys.exit(1)

    tweets = load_tweets(args[0])
    print(f"Profile: {PROFILE}")
    print(f"Thread: {len(tweets)} tweet(s)")
    for i, t in enumerate(tweets):
        img_note = f" [+{len(t['images'])} img]" if t["images"] else ""
        snippet = t["text"][:80] + ("..." if len(t["text"]) > 80 else "")
        print(f"  {i + 1}. ({len(t['text'])} chars){img_note} {snippet}")

    compose_thread(tweets, PROFILE)


if __name__ == "__main__":
    main()
