"""The `validate` command: check a document against a JSON-Schema-style file.

Supports the subset that `jsonlens schema` writes plus a few common
keywords: type (string or list), properties, required, items, enum,
minimum, maximum, minLength, maxLength, pattern, additionalProperties,
minItems, maxItems, uniqueItems, anyOf, oneOf and local $ref ("#/..."). Unknown keywords are ignored.
"""

import json
import re

from .errors import JsonLensError
from .loader import load
from .paths import format_path


def _type_ok(value, name):
    if name == "null":
        return value is None
    if name == "boolean":
        return isinstance(value, bool)
    if name == "integer":
        return (isinstance(value, int) and not isinstance(value, bool)) or (
            isinstance(value, float) and value.is_integer()
        )
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if name == "string":
        return isinstance(value, str)
    if name == "array":
        return isinstance(value, list)
    if name == "object":
        return isinstance(value, dict)
    raise JsonLensError(f"schema: unknown type {name!r}")


def _type_name(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    return "array" if isinstance(value, list) else "object"


def _canonical(value):
    """A hashable key where 1 == 1.0 but True != 1 and key order is ignored."""
    if isinstance(value, bool):
        return ("b", value)
    if isinstance(value, (int, float)):
        return ("n", float(value))
    if isinstance(value, list):
        return ("l", tuple(_canonical(v) for v in value))
    if isinstance(value, dict):
        return ("o", tuple(sorted((k, _canonical(v)) for k, v in value.items())))
    return ("s" if isinstance(value, str) else "z", value)


def _resolve(ref, root):
    """Follow a local '#/a/b' reference inside the root schema."""
    if not isinstance(ref, str) or not (ref == "#" or ref.startswith("#/")):
        raise JsonLensError(f"schema: only local '#/...' references are supported, got {ref!r}")
    node = root
    for part in ref[2:].split("/") if ref != "#" else []:
        part = part.replace("~1", "/").replace("~0", "~")
        if isinstance(node, dict) and part in node:
            node = node[part]
        elif isinstance(node, list) and part.isdigit() and int(part) < len(node):
            node = node[int(part)]
        else:
            raise JsonLensError(f"schema: cannot resolve reference {ref!r}")
    return node


def validate(value, schema, trail=(), root=None):
    """Return a list of (trail, message) problems; empty means valid."""
    if not isinstance(schema, dict):
        raise JsonLensError("schema: expected a JSON object at every schema position")
    if root is None:
        root = schema
    if "$ref" in schema:
        return validate(value, _resolve(schema["$ref"], root), trail, root)
    problems = []
    declared = schema.get("type")
    if declared is not None:
        names = [declared] if isinstance(declared, str) else list(declared)
        if not any(_type_ok(value, n) for n in names):
            problems.append(
                (trail, f"expected {' or '.join(names)}, got {_type_name(value)}")
            )
            return problems
    if "enum" in schema and value not in schema["enum"]:
        problems.append(
            (trail, "not one of " + json.dumps(schema["enum"], ensure_ascii=False))
        )
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            problems.append((trail, f"{value} is below minimum {schema['minimum']}"))
        if "maximum" in schema and value > schema["maximum"]:
            problems.append((trail, f"{value} is above maximum {schema['maximum']}"))
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            problems.append((trail, f"shorter than minLength {schema['minLength']}"))
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            problems.append((trail, f"longer than maxLength {schema['maxLength']}"))
        if "pattern" in schema:
            try:
                matched = re.search(schema["pattern"], value)
            except re.error as exc:
                raise JsonLensError(f"schema: bad pattern {schema['pattern']!r}: {exc}")
            if not matched:
                problems.append((trail, f"does not match pattern {schema['pattern']!r}"))
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                problems.append((trail, f"missing required key {key!r}"))
        props = schema.get("properties", {})
        for key, sub in props.items():
            if key in value:
                problems.extend(validate(value[key], sub, trail + (key,), root))
        extra = schema.get("additionalProperties")
        if extra is not None:
            for key in value:
                if key in props:
                    continue
                if extra is False:
                    problems.append((trail + (key,), "additional property not allowed"))
                elif isinstance(extra, dict):
                    problems.extend(validate(value[key], extra, trail + (key,), root))
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            problems.append((trail, f"fewer than minItems {schema['minItems']} items"))
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            problems.append((trail, f"more than maxItems {schema['maxItems']} items"))
        if schema.get("uniqueItems") is True:
            seen = {}
            for index, element in enumerate(value):
                key = _canonical(element)
                if key in seen:
                    problems.append(
                        (trail + (index,), f"duplicate of item {seen[key]}")
                    )
                else:
                    seen[key] = index
    if isinstance(value, list) and "items" in schema:
        for index, element in enumerate(value):
            problems.extend(validate(element, schema["items"], trail + (index,), root))
    if "anyOf" in schema:
        if not any(not validate(value, s, trail, root) for s in schema["anyOf"]):
            problems.append((trail, "does not match any of the anyOf schemas"))
    if "oneOf" in schema:
        hits = sum(1 for s in schema["oneOf"] if not validate(value, s, trail, root))
        if hits == 0:
            problems.append((trail, "does not match any of the oneOf schemas"))
        elif hits > 1:
            problems.append((trail, f"matches {hits} of the oneOf schemas, expected exactly 1"))
    return problems


def add_parser(sub):
    p = sub.add_parser("validate", help="check a document against a schema file")
    p.add_argument("file", help="JSON file, or '-' for stdin")
    p.add_argument("schema", help="schema file (for example from `jsonlens schema`)")
    p.add_argument("-q", "--quiet", action="store_true", help="exit code only")
    p.set_defaults(func=run)


def run(args):
    if args.file == "-" and args.schema == "-":
        raise JsonLensError("only one of FILE and SCHEMA can be '-'")
    data = load(args.file)
    schema = load(args.schema)
    problems = validate(data, schema)
    if not problems:
        if not args.quiet:
            print("valid")
        return 0
    if not args.quiet:
        for trail, message in problems:
            print(f"{format_path(trail)}: {message}")
        count = len(problems)
        print(f"{count} problem{'s' if count != 1 else ''}")
    return 1
