"""The `schema` command: infer a JSON-Schema-style description of a document."""

import json

from .loader import load


class Node:
    """Accumulated shape of every value seen at one position."""

    def __init__(self):
        self.types = set()
        self.props = {}  # key -> Node (insertion ordered)
        self.counts = {}  # key -> number of objects containing key
        self.objects = 0
        self.items = None  # Node for array elements, or None

    def add(self, value):
        if value is None:
            self.types.add("null")
        elif isinstance(value, bool):
            self.types.add("boolean")
        elif isinstance(value, int):
            self.types.add("integer")
        elif isinstance(value, float):
            self.types.add("number")
        elif isinstance(value, str):
            self.types.add("string")
        elif isinstance(value, list):
            self.types.add("array")
            for element in value:
                if self.items is None:
                    self.items = Node()
                self.items.add(element)
        elif isinstance(value, dict):
            self.types.add("object")
            self.objects += 1
            for key, child in value.items():
                self.props.setdefault(key, Node()).add(child)
                self.counts[key] = self.counts.get(key, 0) + 1

    def to_schema(self):
        types = set(self.types)
        if "integer" in types and "number" in types:
            types.discard("integer")
        schema = {}
        ordered = sorted(types)
        if not ordered:
            return schema
        schema["type"] = ordered[0] if len(ordered) == 1 else ordered
        if "object" in types:
            schema["properties"] = {k: n.to_schema() for k, n in self.props.items()}
            required = [k for k in self.props if self.counts[k] == self.objects]
            if required:
                schema["required"] = required
        if "array" in types and self.items is not None:
            schema["items"] = self.items.to_schema()
        return schema


def infer(data):
    node = Node()
    node.add(data)
    return node.to_schema()


def infer_many(documents):
    """Infer one schema that fits every document in DOCUMENTS."""
    node = Node()
    for doc in documents:
        node.add(doc)
    return node.to_schema()


def add_parser(sub):
    p = sub.add_parser("schema", help="infer a schema from the document")
    p.add_argument("file", help="JSON file, or '-' for stdin")
    p.add_argument("--compact", action="store_true", help="single-line JSON output")
    p.add_argument(
        "--lines",
        action="store_true",
        help="treat the input as JSON Lines and infer one schema for all records",
    )
    p.set_defaults(func=run)


def run(args):
    if args.lines:
        from .loader import parse, read_text

        name = "<stdin>" if args.file == "-" else args.file
        docs = []
        for number, line in enumerate(read_text(args.file).splitlines(), 1):
            if line.strip():
                docs.append(parse(line, f"{name}:{number}"))
        schema = infer_many(docs)
    else:
        schema = infer(load(args.file))
    if args.compact:
        print(json.dumps(schema, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(schema, ensure_ascii=False, indent=2))
    return 0
