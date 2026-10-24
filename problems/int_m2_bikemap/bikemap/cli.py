"""Command line entry point: python -m bikemap [--base-url URL] [--api-key KEY] <command>."""
from __future__ import annotations

import argparse
import os
import sys

from . import http
from .errors import BikemapError

DEFAULT_BASE_URL = "http://127.0.0.1:8700"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bikemap", description="Ride tools for the Pathfinder maps API")
    parser.add_argument("--base-url", default=os.environ.get("BIKEMAP_BASE_URL", DEFAULT_BASE_URL),
                        help="API base URL (env BIKEMAP_BASE_URL)")
    parser.add_argument("--api-key", default=os.environ.get("BIKEMAP_API_KEY"),
                        help="API key (env BIKEMAP_API_KEY)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("health", help="check that the API is reachable")
    return parser


def cmd_health(args: argparse.Namespace) -> int:
    response = http.send("GET", args.base_url.rstrip("/") + "/v1/health", timeout=3)
    response.raise_for_status()
    print(response.json().get("status", "unknown"))
    return 0


COMMANDS = {"health": cmd_health}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return COMMANDS[args.command](args)
    except BikemapError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
