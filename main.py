#!/usr/bin/env python3
"""The Daily Tensor — AI News, Victorian Style."""

import argparse
import http.server
import functools
from pathlib import Path
from config import EDITIONS_DIR, SERVE_PORT


def cmd_generate(args):
    from generator import build_edition
    build_edition(send_telegram=not args.no_telegram)


def cmd_serve(args):
    port = args.port or SERVE_PORT
    EDITIONS_DIR.mkdir(parents=True, exist_ok=True)

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(EDITIONS_DIR))
    server = http.server.HTTPServer(("0.0.0.0", port), handler)

    print(f"\n  The Daily Tensor is being served at:")
    print(f"  http://localhost:{port}/latest.html\n")

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


def main():
    parser = argparse.ArgumentParser(
        description="The Daily Tensor — All the Intelligence That's Fit to Print",
    )
    sub = parser.add_subparsers(dest="command", required=True)

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

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
