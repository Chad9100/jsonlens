"""Reading JSON from a file path or from stdin ("-")."""

import json
import sys

from .errors import JsonLensError


def read_text(source):
    """Return the decoded text of SOURCE ("-" means stdin). Strips a UTF-8 BOM."""
    if source == "-":
        raw = sys.stdin.buffer.read()
    else:
        try:
            with open(source, "rb") as fh:
                raw = fh.read()
        except FileNotFoundError:
            raise JsonLensError(f"file not found: {source}") from None
        except IsADirectoryError:
            raise JsonLensError(f"{source} is a directory, not a JSON file") from None
        except PermissionError:
            raise JsonLensError(f"permission denied: {source}") from None
        except OSError as exc:
            raise JsonLensError(f"cannot read {source}: {exc.strerror or exc}") from None
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        name = "<stdin>" if source == "-" else source
        raise JsonLensError(
            f"{name}: not valid UTF-8 (bad byte at offset {exc.start})"
        ) from None


def parse(text, name="<input>"):
    if not text.strip():
        raise JsonLensError(f"{name}: empty input, expected a JSON document")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise JsonLensError(
            f"{name}: invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from None
    except RecursionError:
        raise JsonLensError(f"{name}: JSON is nested too deeply") from None


def load(source):
    """Load and parse one JSON document from SOURCE."""
    name = "<stdin>" if source == "-" else source
    return parse(read_text(source), name)
