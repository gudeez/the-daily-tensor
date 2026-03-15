#!/usr/bin/env python3
"""
Export X/Twitter session cookies for use with The Daily Tensor.

This opens a browser window where you log into X manually.
After login, cookies are saved to data/x_cookies.json.

Usage: python3 export_x_cookies.py
"""
from scrapling.fetchers import StealthyFetcher
from pathlib import Path
import json
import time


def main():
    print("\n  X Cookie Exporter for The Daily Tensor")
    print("  " + "=" * 40)
    print("\n  A browser window will open. Log into X/Twitter.")
    print("  After you're logged in and see your feed, come back here")
    print("  and press Enter.\n")

    # Open X login page in visible browser
    page = StealthyFetcher.fetch(
        "https://x.com/login",
        headless=False,  # Visible so user can log in
        network_idle=True,
    )

    input("  Press Enter after you've logged into X...")

    # Get cookies from the browser session
    # Note: StealthyFetcher may not expose cookies directly,
    # so we'll use a playwright-based approach instead
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            pg = context.new_page()
            pg.goto("https://x.com/login")

            print("\n  Log into X in the browser window...")
            print("  Press Enter here when you see your feed.\n")
            input("  Press Enter to save cookies...")

            cookies = context.cookies()
            browser.close()

            # Save cookies
            cookie_path = Path(__file__).parent / "data" / "x_cookies.json"
            cookie_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert to simple format
            simple_cookies = []
            for c in cookies:
                if "x.com" in c.get("domain", "") or "twitter.com" in c.get("domain", ""):
                    simple_cookies.append({
                        "name": c["name"],
                        "value": c["value"],
                        "domain": c["domain"],
                        "path": c.get("path", "/"),
                    })

            cookie_path.write_text(json.dumps(simple_cookies, indent=2))
            print(f"\n  Saved {len(simple_cookies)} cookies to {cookie_path}")
            print("  The Daily Tensor will now use these for X scraping.\n")

    except Exception as e:
        print(f"\n  Error: {e}")
        print("  You can manually export cookies using a browser extension")
        print("  and save them to data/x_cookies.json\n")


if __name__ == "__main__":
    main()
