#!/usr/bin/env python3
"""Post a thread to X (Twitter) via Playwright CDP connection to Edge.

Prerequisites:
    1. Close all Edge windows
    2. Launch Edge with debug port:
       "/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" \
           --remote-debugging-port=9225 --remote-debugging-address=0.0.0.0 \
           --remote-allow-origins=* --user-data-dir=/tmp/edge-profile
    3. If first run, log in to X in the Edge window
    4. Run this script

Usage:
    python3 scripts/post-thread.py tweets.json [--compose-only] [--post]
    python3 scripts/post-thread.py tweets.json              # compose only, wait for approval
    python3 scripts/post-thread.py --post                   # post a previously composed thread

Input: JSON array of strings (one per tweet).

Modes:
    --compose-only  Type all tweets into the compose dialog, then exit (default).
                    Review the thread in the browser before posting.
    --post          Find the open compose dialog and click Post all.
    No flags        Same as --compose-only.

Environment:
    CDP_URL         Browser debug endpoint (default: http://localhost:9225)
"""

import json
import os
import sys
import time

from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout

COMPOSE_URL = "https://x.com/compose/post"
MAX_TWEET_LEN = 280


def load_tweets(source: str) -> list[str]:
    with open(source) as f:
        data = json.load(f)

    if not isinstance(data, list) or not all(isinstance(t, str) for t in data):
        print("Error: input must be a JSON array of strings", file=sys.stderr)
        sys.exit(1)

    for i, tweet in enumerate(data):
        if len(tweet) > MAX_TWEET_LEN:
            print(f"Error: tweet {i + 1} is {len(tweet)} chars (max {MAX_TWEET_LEN})", file=sys.stderr)
            sys.exit(1)

    return data


def connect(cdp_url: str):
    """Connect to running browser via CDP. Returns (playwright, browser, context, page)."""
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp(cdp_url)
    context = browser.contexts[0] if browser.contexts else browser.new_context()
    page = context.new_page()
    return pw, browser, context, page


def check_login(page) -> bool:
    """Navigate to X home and check if logged in."""
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


def open_login(cdp_url: str):
    """Open X login page and exit. User logs in manually."""
    pw, browser, context, page = connect(cdp_url)
    page.goto("https://x.com/login", wait_until="domcontentloaded")
    print("Login page opened. Log in, then re-run the script.")
    pw.stop()


def compose_thread(tweets: list[str], cdp_url: str):
    """Type all tweets into the compose dialog using + button. Does NOT post."""
    pw, browser, context, page = connect(cdp_url)

    if not check_login(page):
        print("Not logged in. Opening login page.")
        page.goto("https://x.com/login", wait_until="domcontentloaded")
        print("Log in to X, then re-run the script.")
        pw.stop()
        sys.exit(1)

    print("Logged in. Opening compose dialog...")
    page.goto(COMPOSE_URL, wait_until="domcontentloaded")
    time.sleep(3)

    for idx, tweet in enumerate(tweets):
        textarea_id = f"tweetTextarea_{idx}"
        editor = page.locator(f'[data-testid="{textarea_id}"]').first
        editor.wait_for(timeout=10000)
        editor.click()
        time.sleep(0.5)

        lines = tweet.split("\n")
        for i, line in enumerate(lines):
            page.keyboard.type(line, delay=12)
            if i < len(lines) - 1:
                page.keyboard.press("Enter")

        print(f"  [{idx + 1}/{len(tweets)}] Typed ({len(tweet)} chars)")

        if idx < len(tweets) - 1:
            time.sleep(0.5)
            add_btn = page.locator('[data-testid="addButton"]').first
            add_btn.wait_for(timeout=5000)
            add_btn.click()
            time.sleep(1)

    print(f"\nAll {len(tweets)} tweets composed. Review in browser.")
    print("When ready, run: python3 scripts/post-thread.py --post")
    pw.stop()


def post_thread(cdp_url: str):
    """Find the open compose dialog and click Post all."""
    pw, browser, context, page = connect(cdp_url)

    page.goto(COMPOSE_URL, wait_until="domcontentloaded")
    time.sleep(2)

    post_btn = page.locator('[data-testid="tweetButton"], [data-testid="tweetButtonInline"]').first
    try:
        post_btn.wait_for(timeout=5000)
    except PwTimeout:
        print("Error: no compose dialog found. Compose the thread first.", file=sys.stderr)
        pw.stop()
        sys.exit(1)

    post_btn.click()
    time.sleep(5)
    print("Thread posted.")
    pw.stop()


def compose_and_post(tweets: list[str], cdp_url: str):
    """Compose all tweets and immediately post. Single connection, no disconnect."""
    pw, browser, context, page = connect(cdp_url)

    if not check_login(page):
        print("Not logged in. Opening login page.")
        page.goto("https://x.com/login", wait_until="domcontentloaded")
        print("Log in to X, then re-run the script.")
        pw.stop()
        sys.exit(1)

    print("Logged in. Opening compose dialog...")
    page.goto(COMPOSE_URL, wait_until="domcontentloaded")
    time.sleep(3)

    for idx, tweet in enumerate(tweets):
        textarea_id = f"tweetTextarea_{idx}"
        editor = page.locator(f'[data-testid="{textarea_id}"]').first
        editor.wait_for(timeout=10000)
        editor.click()
        time.sleep(0.5)

        lines = tweet.split("\n")
        for i, line in enumerate(lines):
            page.keyboard.type(line, delay=12)
            if i < len(lines) - 1:
                page.keyboard.press("Enter")

        print(f"  [{idx + 1}/{len(tweets)}] Typed ({len(tweet)} chars)")

        if idx < len(tweets) - 1:
            time.sleep(0.5)
            add_btn = page.locator('[data-testid="addButton"]').first
            add_btn.wait_for(timeout=5000)
            add_btn.click()
            time.sleep(1)

    print(f"All {len(tweets)} tweets composed. Posting...")
    time.sleep(2)

    post_btn = page.locator('[data-testid="tweetButton"], [data-testid="tweetButtonInline"]').first
    post_btn.wait_for(timeout=5000)
    post_btn.click()
    time.sleep(5)

    print("Thread posted.")
    pw.stop()


def main():
    cdp_url = os.environ.get("CDP_URL", "http://localhost:9225")

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]

    if "--post" in flags:
        post_thread(cdp_url)
        return

    if not args:
        print(f"Usage: {sys.argv[0]} <tweets.json> [--compose-only | --post-now]", file=sys.stderr)
        print(f"       {sys.argv[0]} --post  (post a previously composed thread)", file=sys.stderr)
        sys.exit(1)

    tweets = load_tweets(args[0])
    print(f"Thread: {len(tweets)} tweet(s)")
    for i, t in enumerate(tweets):
        print(f"  {i + 1}. ({len(t)} chars) {t[:80]}{'...' if len(t) > 80 else ''}")

    if "--post-now" in flags:
        compose_and_post(tweets, cdp_url)
    else:
        compose_thread(tweets, cdp_url)


if __name__ == "__main__":
    main()
