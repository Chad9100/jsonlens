"""The `tree` command: a depth-limited outline of a JSON document."""

import json

from .errors import JsonLensError
from .loader import load

_UNICODE = ("├── ", "└── ", "│   ", "    ", "…")
_ASCII = ("|-- ", "`-- ", "|   ", "    ", "...")


def _plural(n, word):
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def _children(value):
    if isinstance(value, dict):
        return list(value.items())
    if isinstance(value, list):
        return [(f"[{i}]", v) for i, v in enumerate(value)]
    return []


def _leaf(value, width):
    text = json.dumps(value, ensure_ascii=False)
    if len(text) > width:
        text = text[: max(width - 1, 1)] + "…"
    return text


def _describe(label, value, depth_left, width, glyphs):
    if isinstance(value, dict):
        info = f"object, {_plural(len(value), 'key')}"
    elif isinstance(value, list):
        info = f"array, {_plural(len(value), 'item')}"
    else:
        return f"{label}: {_leaf(value, width)}"
    suffix = f" {glyphs[4]}" if value and depth_left <= 0 else ""
    return f"{label} ({info}){suffix}"


def render(data, depth=3, max_items=10, width=40, ascii_only=False):
    """Return the tree as a list of lines."""
    glyphs = _ASCII if ascii_only else _UNICODE
    tee, elbow, bar, blank, dots = glyphs
    lines = [_describe("$", data, depth, width, glyphs)]

    def walk(value, prefix, depth_left):
        if depth_left <= 0:
            return
        kids = _children(value)
        shown = kids[:max_items]
        hidden = len(kids) - len(shown)
        for i, (label, child) in enumerate(shown):
            last = i == len(shown) - 1 and not hidden
            lines.append(
                prefix + (elbow if last else tee) + _describe(label, child, depth_left - 1, width, glyphs)
            )
            walk(child, prefix + (blank if last else bar), depth_left - 1)
        if hidden:
            lines.append(prefix + elbow + f"{dots} {hidden} more")

    walk(data, "", depth)
    return lines


def add_parser(sub):
    p = sub.add_parser("tree", help="show a depth-limited tree of the document")
    p.add_argument("file", help="JSON file, or '-' for stdin")
    p.add_argument("-d", "--depth", type=int, default=3, help="levels to show (default 3)")
    p.add_argument("--max-items", type=int, default=10, help="children shown per node (default 10)")
    p.add_argument("--width", type=int, default=40, help="max characters of a leaf value (default 40)")
    p.add_argument("--ascii", action="store_true", help="use plain ASCII line drawing")
    p.set_defaults(func=run)


def run(args):
    if args.depth < 0:
        raise JsonLensError("--depth must be 0 or greater")
    if args.max_items < 1:
        raise JsonLensError("--max-items must be at least 1")
    data = load(args.file)
    for line in render(data, args.depth, args.max_items, args.width, args.ascii):
        print(line)
    return 0
