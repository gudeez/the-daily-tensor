#!/usr/bin/env python3
"""The Daily Tensor — AI News, Victorian Style."""

import argparse
import http.server
import functools
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from config import EDITIONS_DIR, SERVE_PORT

CST = timezone(timedelta(hours=-6))


class NewspaperHandler(http.server.SimpleHTTPRequestHandler):
    """Serves editions dir, routing / to latest.html."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(EDITIONS_DIR), **kwargs)

    def do_GET(self):
        if self.path == "/" or self.path == "":
            self.path = "/latest.html"
        super().do_GET()


def cmd_generate(args):
    from generator import build_edition
    build_edition(send_telegram=not args.no_telegram)


def cmd_serve(args):
    port = args.port or int(os.environ.get("PORT", SERVE_PORT))
    EDITIONS_DIR.mkdir(parents=True, exist_ok=True)

    # Create a placeholder if no edition exists yet
    latest = EDITIONS_DIR / "latest.html"
    if not latest.exists():
        latest.write_text("<html><body><h1>The Daily Tensor</h1><p>No edition generated yet. Run: python3 main.py generate</p></body></html>")

    server = http.server.HTTPServer(("0.0.0.0", port), NewspaperHandler)

    print(f"\n  The Daily Tensor is being served at:")
    print(f"  http://localhost:{port}/\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Press stopped. Good day, sir.")
        server.shutdown()


def cmd_run(args):
    from generator import build_edition
    path = build_edition(send_telegram=not args.no_telegram)
    if path:
        cmd_serve(args)


def cmd_schedule(args):
    import schedule

    def job():
        now = datetime.now(CST)
        print(f"\n  [{now.strftime('%Y-%m-%d %H:%M %Z')}] Generating today's edition...")
        from generator import build_edition
        try:
            build_edition(send_telegram=not args.no_telegram)
            print("  Edition generated successfully.")
        except Exception as e:
            print(f"  Error generating edition: {e}")

    schedule.every().day.at("08:30").do(job)

    now = datetime.now(CST)
    print(f"\n  The Daily Tensor — Scheduler active")
    print(f"  Current time (CST): {now.strftime('%Y-%m-%d %H:%M')}")
    print(f"  Next edition at:    08:30 CST daily")
    print(f"  Press Ctrl+C to stop.\n")

    try:
        while True:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        print("\n  Scheduler stopped. Good day, sir.")


def main():
    parser = argparse.ArgumentParser(
        description="The Daily Tensor — All the Intelligence That's Fit to Print",
    )
    sub = parser.add_subparsers(dest="command")

    gen = sub.add_parser("generate", help="Fetch news and generate today's edition")
    gen.add_argument("--no-telegram", action="store_true", help="Skip Telegram notification")
    gen.set_defaults(func=cmd_generate)

    srv = sub.add_parser("serve", help="Serve the newspaper locally")
    srv.add_argument("--port", type=int, default=None, help=f"Port (default: {SERVE_PORT})")
    srv.set_defaults(func=cmd_serve)

    run = sub.add_parser("run", help="Generate then serve")
    run.add_argument("--port", type=int, default=None, help=f"Port (default: {SERVE_PORT})")
    run.add_argument("--no-telegram", action="store_true", help="Skip Telegram notification")
    run.set_defaults(func=cmd_run)

    sched = sub.add_parser("schedule", help="Run scheduler — generates edition daily at 8:30 AM CST")
    sched.add_argument("--no-telegram", action="store_true", help="Skip Telegram notification")
    sched.set_defaults(func=cmd_schedule)

    args = parser.parse_args()

    # Default to serve if no command given (for Railway/deployment)
    if args.command is None:
        args.port = None
        args.no_telegram = False
        cmd_serve(args)
    else:
        args.func(args)


if __name__ == "__main__":
    main()
