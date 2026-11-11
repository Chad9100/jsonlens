"""The `diff` command: structural comparison of two JSON documents."""

import json

from .errors import JsonLensError
from .loader import load
from .paths import format_path


def _same_kind(a, b):
    """Booleans are not numbers; ints and floats compare as numbers."""
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return True
    return type(a) is type(b)


def diff(a, b, trail=None):
    """Return a list of (kind, trail, old, new); kind is 'added', 'removed' or 'changed'."""
    trail = trail or []
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for key in a:
            if key in b:
                out.extend(diff(a[key], b[key], trail + [key]))
            else:
                out.append(("removed", trail + [key], a[key], None))
        for key in b:
            if key not in a:
                out.append(("added", trail + [key], None, b[key]))
        return out
    if isinstance(a, list) and isinstance(b, list):
        out = []
        for i in range(min(len(a), len(b))):
            out.extend(diff(a[i], b[i], trail + [i]))
        for i in range(len(b), len(a)):
            out.append(("removed", trail + [i], a[i], None))
        for i in range(len(a), len(b)):
            out.append(("added", trail + [i], None, b[i]))
        return out
    if _same_kind(a, b) and a == b:
        return []
    return [("changed", trail, a, b)]


def _short(value, width=60):
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return text if len(text) <= width else text[: width - 1] + "…"


def format_change(change):
    kind, trail, old, new = change
    path = format_path(trail)
    if kind == "added":
        return f"+ {path}: {_short(new)}"
    if kind == "removed":
        return f"- {path}: {_short(old)}"
    return f"~ {path}: {_short(old)} -> {_short(new)}"


def add_parser(sub):
    p = sub.add_parser("diff", help="structural diff of two JSON documents")
    p.add_argument("a", help="first JSON file, or '-' for stdin")
    p.add_argument("b", help="second JSON file, or '-' for stdin")
    p.add_argument("--json", action="store_true", help="emit the changes as a JSON array")
    p.add_argument("-q", "--quiet", action="store_true", help="print nothing, only set the exit code")
    p.set_defaults(func=run)


def run(args):
    if args.a == "-" and args.b == "-":
        raise JsonLensError("only one of the two inputs can be '-' (stdin)")
    changes = diff(load(args.a), load(args.b))
    if not args.quiet:
        if args.json:
            print(
                json.dumps(
                    [
                        {"change": k, "path": format_path(t), "old": o, "new": n}
                        for k, t, o, n in changes
                    ],
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            for change in changes:
                print(format_change(change))
            if changes:
                print(f"{len(changes)} difference{'s' if len(changes) != 1 else ''}")
    return 1 if changes else 0
