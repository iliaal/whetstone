#!/usr/bin/env python3
"""Compose a thread on X (Twitter) via the compound-engineering Edge profile.

Drafts the thread only -- the user clicks Post manually in the browser.

Prerequisites:
    1. Auto-launches the compound-engineering Edge profile if not already running
       (via edge-cdp ensure compound-engineering). First run: log in to X manually.
    2. Provide a JSON file containing an array of tweet strings.

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


def compose_thread(tweets: list[str], profile: str):
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
        print(f"  {i + 1}. ({len(t)} chars) {t[:80]}{'...' if len(t) > 80 else ''}")

    compose_thread(tweets, PROFILE)


if __name__ == "__main__":
    main()
