"""Command line entry point.

Exit codes: 0 success, 1 "no result" (get found nothing / diff found
differences), 2 error (bad file, bad JSON, bad path, bad usage).
"""

import argparse
import sys

from . import __version__
from .errors import JsonLensError

COMMANDS = []


def build_parser():
    parser = argparse.ArgumentParser(
        prog="jsonlens",
        description="Query, explore, infer schemas from and diff JSON files. "
        "Use '-' as a file name to read from stdin.",
    )
    parser.add_argument("--version", action="version", version=f"jsonlens {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    for module in COMMANDS:
        module.add_parser(sub)
    return parser


def _utf8_stdio():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError, OSError):
            pass


def main(argv=None):
    _utf8_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help(sys.stderr)
        return 2
    try:
        return args.func(args)
    except JsonLensError as exc:
        print(f"jsonlens: error: {exc}", file=sys.stderr)
        return 2
    except BrokenPipeError:
        return 0
