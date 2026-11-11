"""Path expressions and the `get` command.

Syntax: `a.b[0].c`, `items[-1]`, `users[*].name`, `config.*`,
`["key.with.dots"]`, `..name` (that key at any depth), `..*` (every
descendant). A leading `$` (root) is optional; `$` alone is the root.
"""

import json
import re
import sys

from .errors import JsonLensError
from .loader import load

WILD = "*"
_INT = re.compile(r"-?\d+")
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


def parse_path(text):
    """Parse TEXT into a list of tokens: str (key), int (index) or WILD marker.

    Wildcards are represented as the `Wild` singleton so they never clash
    with a literal key named "*" (written ["*"]).
    """
    s = text.strip()
    n = len(s)
    i = 1 if s.startswith("$") else 0
    tokens = []
    first = True
    while i < n:
        c = s[i]
        if c == "." and s.startswith("..", i):
            i += 2
            if i >= n or s[i] == ".":
                raise JsonLensError(f"bad path {text!r}: nothing to search for after '..' at position {i}")
            tokens.append(Descend)
            if s[i] == "*":
                tokens.append(Wild)
                i += 1
            elif s[i] != "[":
                i, key = _bare_key(s, i)
                tokens.append(key)
        elif c == ".":
            i += 1
            if i >= n or s[i] in ".[":
                raise JsonLensError(f"bad path {text!r}: empty key after '.' at position {i}")
            if s[i] == "*":
                tokens.append(Wild)
                i += 1
            else:
                i, key = _bare_key(s, i)
                tokens.append(key)
        elif c == "[":
            i, tok = _bracket(s, i, text)
            tokens.append(tok)
        elif first:
            i, key = _bare_key(s, i)
            tokens.append(key)
        else:
            raise JsonLensError(f"bad path {text!r}: unexpected {c!r} at position {i}")
        first = False
    return tokens


class _WildType:
    def __repr__(self):
        return "Wild"


Wild = _WildType()


class _DescendType:
    def __repr__(self):
        return "Descend"


Descend = _DescendType()


def _walk(value, trail):
    """Yield (trail, value) for VALUE and every descendant, parents first."""
    yield trail, value
    if isinstance(value, dict):
        for k, v in value.items():
            yield from _walk(v, trail + [k])
    elif isinstance(value, list):
        for k, v in enumerate(value):
            yield from _walk(v, trail + [k])


def _bare_key(s, i):
    j = i
    while j < len(s) and s[j] not in ".[":
        j += 1
    return j, s[i:j]


def _bracket(s, i, text):
    j = i + 1
    if j >= len(s):
        raise JsonLensError(f"bad path {text!r}: unclosed '[' at position {i}")
    if s[j] == '"':
        try:
            key, end = json.JSONDecoder().raw_decode(s, j)
        except json.JSONDecodeError:
            raise JsonLensError(f"bad path {text!r}: bad quoted key at position {j}") from None
        tok = key
        j = end
    elif s[j] == "*":
        tok = Wild
        j += 1
    else:
        m = _INT.match(s, j)
        if not m:
            raise JsonLensError(
                f"bad path {text!r}: expected index, '*' or quoted key inside [] at position {j}"
            )
        tok = int(m.group())
        j = m.end()
    if j >= len(s) or s[j] != "]":
        raise JsonLensError(f"bad path {text!r}: expected ']' at position {j}")
    return j + 1, tok


def format_path(tokens):
    """Render tokens back into canonical path text (`$` for the root)."""
    out = ""
    for tok in tokens:
        if tok is Wild:
            out += "[*]"
        elif isinstance(tok, int):
            out += f"[{tok}]"
        elif _IDENT.match(tok):
            out += f".{tok}" if out else tok
        else:
            out += "[" + json.dumps(tok, ensure_ascii=False) + "]"
    return out or "$"


def query(data, tokens):
    """Return a list of (concrete_tokens, value) matches for TOKENS in DATA."""
    current = [([], data)]
    for tok in tokens:
        nxt = []
        for trail, value in current:
            if tok is Descend:
                nxt.extend(_walk(value, trail))
            elif tok is Wild:
                if isinstance(value, dict):
                    nxt.extend((trail + [k], v) for k, v in value.items())
                elif isinstance(value, list):
                    nxt.extend((trail + [k], v) for k, v in enumerate(value))
            elif isinstance(tok, int):
                if isinstance(value, list) and -len(value) <= tok < len(value):
                    idx = tok % len(value)
                    nxt.append((trail + [idx], value[idx]))
            elif isinstance(value, dict) and tok in value:
                nxt.append((trail + [tok], value[tok]))
        current = nxt
        if not current:
            break
    return current


def has_wildcard(tokens):
    return any(t is Wild or t is Descend for t in tokens)


def add_parser(sub):
    p = sub.add_parser("get", help="extract values with a path like users[*].name")
    p.add_argument("file", help="JSON file, or '-' for stdin")
    p.add_argument("path", help="path expression, e.g. a.b[0].c or items[*].id")
    p.add_argument("--raw", action="store_true", help="print strings without quotes")
    p.add_argument("--paths", action="store_true", help="prefix each match with its concrete path")
    p.add_argument("--compact", action="store_true", help="single-line JSON output")
    p.set_defaults(func=run)


def _dump(value, compact):
    if compact:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return json.dumps(value, ensure_ascii=False, indent=2)


def run(args):
    tokens = parse_path(args.path)
    data = load(args.file)
    matches = query(data, tokens)
    if not matches:
        print(f"jsonlens: no match for {args.path!r}", file=sys.stderr)
        return 1

    def show(value):
        if args.raw and isinstance(value, str):
            return value
        return _dump(value, args.compact)

    if args.paths:
        for trail, value in matches:
            print(f"{format_path(trail)} = {_dump(value, True) if not args.raw or not isinstance(value, str) else value}")
    elif has_wildcard(tokens):
        if args.raw:
            for _, value in matches:
                print(show(value))
        else:
            print(_dump([v for _, v in matches], args.compact))
    else:
        print(show(matches[0][1]))
    return 0
