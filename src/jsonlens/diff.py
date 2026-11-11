"""The `diff` command: structural comparison of two JSON documents."""

import json

from .errors import JsonLensError
from .loader import load
from .paths import KeyedItem, format_path


def _same_kind(a, b):
    """Booleans are not numbers; ints and floats compare as numbers."""
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return True
    return type(a) is type(b)


def _keyed(items, key):
    """Map identity -> element if every item is an object with a unique
    string/number key value; otherwise None (caller falls back to indexes)."""
    seen = {}
    for item in items:
        if not isinstance(item, dict) or key not in item:
            return None
        value = item[key]
        if isinstance(value, bool) or not isinstance(value, (str, int, float)):
            return None
        if value in seen:
            return None
        seen[value] = item
    return seen


def diff(a, b, trail=None, key=None):
    """Return a list of (kind, trail, old, new); kind is 'added', 'removed' or 'changed'.

    With KEY, arrays of objects that all carry a unique KEY value are matched
    by that value instead of by position."""
    trail = trail or []
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in a:
            if k in b:
                out.extend(diff(a[k], b[k], trail + [k], key))
            else:
                out.append(("removed", trail + [k], a[k], None))
        for k in b:
            if k not in a:
                out.append(("added", trail + [k], None, b[k]))
        return out
    if isinstance(a, list) and isinstance(b, list):
        out = []
        if key is not None:
            ma, mb = _keyed(a, key), _keyed(b, key)
            if ma is not None and mb is not None:
                for ident, item in ma.items():
                    t = trail + [KeyedItem(key, ident)]
                    if ident in mb:
                        out.extend(diff(item, mb[ident], t, key))
                    else:
                        out.append(("removed", t, item, None))
                for ident, item in mb.items():
                    if ident not in ma:
                        out.append(("added", trail + [KeyedItem(key, ident)], None, item))
                return out
        for i in range(min(len(a), len(b))):
            out.extend(diff(a[i], b[i], trail + [i], key))
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
    p.add_argument(
        "--key",
        metavar="FIELD",
        help="match array elements by this field instead of by index "
        "(arrays whose objects lack a unique FIELD still compare by index)",
    )
    p.add_argument("--json",action="store_true", help="emit the changes as a JSON array")
    p.add_argument("-q", "--quiet", action="store_true", help="print nothing, only set the exit code")
    p.set_defaults(func=run)


def run(args):
    if args.a == "-" and args.b == "-":
        raise JsonLensError("only one of the two inputs can be '-' (stdin)")
    changes = diff(load(args.a), load(args.b), key=args.key)
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
