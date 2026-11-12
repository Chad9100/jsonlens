"""Path expressions and the `get` command.

Syntax: `a.b[0].c`, `items[-1]`, `users[*].name`, `config.*`,
`["key.with.dots"]`, `..name` (that key at any depth), `..*` (every
descendant), `users[?(@.age > 30)]` (children where a comparison holds). A leading `$` (root) is optional; `$` alone is the root.
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
    elif s[j] == "?":
        end = _find_close(s, j)
        if end < 0:
            raise JsonLensError(f"bad path {text!r}: unclosed '[' at position {i}")
        return end + 1, _parse_filter(s[j + 1 : end], text)
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


_FILTER_OPS = ("==", "!=", "=~", "<=", ">=", "<", ">")


def _find_close(s, j):
    """Index of the ']' closing a filter that starts at J, skipping quotes."""
    quote = None
    k = j
    while k < len(s):
        c = s[k]
        if quote:
            if c == "\\":
                k += 1
            elif c == quote:
                quote = None
        elif c in "\"'":
            quote = c
        elif c == "]":
            return k
        k += 1
    return -1


class Filter:
    """`[?(@.a.b > 3)]`: keep children where the relative path compares true."""

    def __init__(self, rel, op, literal):
        self.rel = rel
        self.op = op
        self.literal = literal

    def __repr__(self):
        return f"Filter({self.rel!r}, {self.op!r}, {self.literal!r})"

    def __eq__(self, other):
        return isinstance(other, Filter) and (self.rel, self.op, self.literal) == (
            other.rel,
            other.op,
            other.literal,
        )

    __hash__ = None

    def matches(self, item):
        value = item
        for tok in self.rel:
            if isinstance(tok, int):
                if isinstance(value, list) and -len(value) <= tok < len(value):
                    value = value[tok]
                else:
                    return False
            elif isinstance(value, dict) and tok in value:
                value = value[tok]
            else:
                return False
        if self.op is None:
            return True
        return _compare(value, self.op, self.literal)


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _compare(a, op, b):
    if op == "=~":
        return isinstance(a, str) and re.search(b, a) is not None
    if op in ("==", "!="):
        same = a == b and (type(a) is type(b) or (_is_num(a) and _is_num(b)))
        return same if op == "==" else not same
    if (_is_num(a) and _is_num(b)) or (isinstance(a, str) and isinstance(b, str)):
        return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op]
    return False


class FilterOr:
    """`[?(A && B || C)]`: OR of AND-groups of Filter terms (`&&` binds tighter)."""

    def __init__(self, groups):
        self.groups = groups

    def __repr__(self):
        return f"FilterOr({self.groups!r})"

    def __eq__(self, other):
        return isinstance(other, FilterOr) and self.groups == other.groups

    __hash__ = None

    def matches(self, item):
        return any(all(t.matches(item) for t in group) for group in self.groups)


def _scan(expr, visit):
    """Call VISIT(k, depth) for each character of EXPR outside quotes; stop when it returns True."""
    quote = None
    depth = 0
    k = 0
    while k < len(expr):
        c = expr[k]
        if quote:
            if c == "\\":
                k += 1
            elif c == quote:
                quote = None
        elif c in "\"'":
            quote = c
        else:
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
            if visit(k, depth):
                return k
        k += 1
    return -1


def _strip_parens(expr):
    """Remove outer parentheses while the first '(' matches the last ')'."""
    expr = expr.strip()
    while expr.startswith("(") and expr.endswith(")"):
        closed_early = _scan(expr[:-1], lambda k, d: d == 0) >= 0
        if closed_early:
            break
        expr = expr[1:-1].strip()
    return expr


def _split_on(expr, sep):
    """Split EXPR on SEP outside quotes and parentheses."""
    parts = []
    start = 0
    k = 0
    while k <= len(expr) - len(sep):
        hit = _scan(expr[k:], lambda i, d: d == 0 and expr.startswith(sep, k + i))
        if hit < 0:
            break
        parts.append(expr[start : k + hit])
        start = k + hit + len(sep)
        k = start
    parts.append(expr[start:])
    return parts


def _parse_filter(body, text):
    expr = _strip_parens(body)
    ors = _split_on(expr, "||")
    if len(ors) > 1 or len(_split_on(expr, "&&")) > 1:
        groups = []
        for part in ors:
            terms = [_parse_term(_strip_parens(t), text) for t in _split_on(part, "&&")]
            groups.append(terms)
        return FilterOr(groups)
    return _parse_term(expr, text)


def _parse_term(expr, text):
    if not expr.startswith("@"):
        raise JsonLensError(f"bad path {text!r}: a filter must start with '@', e.g. [?(@.age > 30)]")
    # find the operator outside of quotes
    quote = None
    pos = op = None
    k = 0
    while k < len(expr):
        c = expr[k]
        if quote:
            if c == "\\":
                k += 1
            elif c == quote:
                quote = None
        elif c in "\"'":
            quote = c
        else:
            for cand in _FILTER_OPS:
                if expr.startswith(cand, k):
                    pos, op = k, cand
                    break
            if op:
                break
        k += 1
    left = expr if op is None else expr[:pos]
    rel = parse_path("$" + left.strip()[1:])
    if any(t is Wild or t is Descend or isinstance(t, (Filter, FilterOr, _WildType)) for t in rel):
        raise JsonLensError(f"bad path {text!r}: wildcards and filters are not allowed inside a filter")
    literal = None
    if op:
        raw = expr[pos + len(op) :].strip()
        if len(raw) >= 2 and raw[0] == "'" and raw[-1] == "'":
            raw = json.dumps(raw[1:-1])
        try:
            literal = json.loads(raw)
        except ValueError:
            raise JsonLensError(
                f"bad path {text!r}: filter value {raw!r} must be a JSON literal (number, \"text\", true, false, null)"
            ) from None
    if op == "=~":
        if not isinstance(literal, str):
            raise JsonLensError(f"bad path {text!r}: '=~' needs a quoted regular expression")
        try:
            re.compile(literal)
        except re.error as exc:
            raise JsonLensError(f"bad path {text!r}: invalid regular expression {literal!r}: {exc}") from None
    return Filter(rel, op, literal)


class KeyedItem(tuple):
    """Display-only token for an array element matched by key (diff --key)."""

    def __new__(cls, field, value):
        return super().__new__(cls, (field, value))


def format_path(tokens):
    """Render tokens back into canonical path text (`$` for the root)."""
    out = ""
    for tok in tokens:
        if isinstance(tok, KeyedItem):
            out += f"[{tok[0]}={json.dumps(tok[1], ensure_ascii=False)}]"
        elif tok is Wild:
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
            elif isinstance(tok, (Filter, FilterOr)):
                kids = (
                    value.items()
                    if isinstance(value, dict)
                    else enumerate(value) if isinstance(value, list) else ()
                )
                nxt.extend((trail + [k], v) for k, v in kids if tok.matches(v))
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
    return any(t is Wild or t is Descend or isinstance(t, (Filter, FilterOr)) for t in tokens)


def add_parser(sub):
    p = sub.add_parser("get", help="extract values with a path like users[*].name")
    p.add_argument("file", help="JSON file, or '-' for stdin")
    p.add_argument("path", help="path expression, e.g. a.b[0].c or items[*].id")
    p.add_argument("--raw", action="store_true", help="print strings without quotes")
    p.add_argument("--paths", action="store_true", help="prefix each match with its concrete path")
    p.add_argument("--compact", action="store_true", help="single-line JSON output")
    p.add_argument(
        "--format",
        choices=["json", "csv", "tsv"],
        default="json",
        help="output format; csv/tsv need a list of objects or plain values",
    )
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

    if args.format != "json":
        if args.paths or args.raw or args.compact:
            raise JsonLensError("--format csv/tsv cannot be combined with --paths, --raw or --compact")
        from . import tabular

        records = tabular.rows_from([v for _, v in matches], not has_wildcard(tokens))
        sys.stdout.write(tabular.render(records, args.format))
        return 0

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
