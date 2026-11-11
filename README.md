# jsonlens

A small command-line tool for looking into JSON files: pull values out with a
path, see the shape as a tree, infer a schema, and diff two documents.
Python 3.10+, standard library only.

```
pip install .
jsonlens --help
```

Every command takes a file name, or `-` to read from stdin. A UTF-8 BOM is
ignored. All output below is real output copied from runs of the tool.

## Example data

`shop.json`:

```json
{
  "shop": "Corner Cafe",
  "open": true,
  "rating": 4.5,
  "menu": [
    {"item": "Espresso", "price": 3, "tags": ["hot", "coffee"]},
    {"item": "Cold Brew", "price": 4.5, "tags": ["cold"]},
    {"item": "Croissant", "price": 3.25, "vegan": false}
  ],
  "owner": {"name": "Maria", "email": null}
}
```

## get

Path syntax: `a.b`, `a[0]`, `a[-1]`, `a[*]` / `a.*` (wildcards), and
`["key.with.dots"]` for awkward keys. `..name` finds a key at any depth
(recursive descent, results in document order, always printed as a list) and
`..*` lists every descendant. A leading `$` is optional.

```
$ jsonlens get shop.json ..name --compact
["Maria","oat milk"]
[exit 0]

$ jsonlens get shop.json ..price --paths
menu[0].price = 3
menu[1].price = 3.25
[exit 0]
```


```
$ jsonlens get shop.json menu[*].item
[
  "Espresso",
  "Cold Brew",
  "Croissant"
]
[exit 0]

$ jsonlens get shop.json menu[-1].price
3.25
[exit 0]

$ jsonlens get shop.json menu[*].price --paths
menu[0].price = 3
menu[1].price = 4.5
menu[2].price = 3.25
[exit 0]

$ jsonlens get shop.json owner.name --raw
Maria
[exit 0]

$ jsonlens get shop.json menu[7]
jsonlens: no match for 'menu[7]'
[exit 1]

$ echo {"a": [1, 2]} | jsonlens get - a[1]
2
[exit 0]
```

Options: `--raw` (unquoted strings), `--paths` (show where each match came
from), `--compact` (single-line JSON).

## tree

```
$ jsonlens tree shop.json --depth 2
$ (object, 5 keys)
├── shop: "Corner Cafe"
├── open: true
├── rating: 4.5
├── menu (array, 3 items)
│   ├── [0] (object, 3 keys) …
│   ├── [1] (object, 3 keys) …
│   └── [2] (object, 3 keys) …
└── owner (object, 2 keys)
    ├── name: "Maria"
    └── email: null
[exit 0]
```

A trailing `…` marks a container whose children are hidden by `--depth`.
Other options: `--max-items`, `--width`, `--ascii`.

## schema

Infers a JSON-Schema-style description. A key is `required` when it appears
in every object seen at that position; mixed types become a list; integers
and floats together become `number`. `--lines` reads JSON Lines.

```
$ jsonlens schema shop.json --compact
{"type":"object","properties":{"shop":{"type":"string"},"open":{"type":"boolean"},"rating":{"type":"number"},"menu":{"type":"array","items":{"type":"object","properties":{"item":{"type":"string"},"price":{"type":"number"},"tags":{"type":"array","items":{"type":"string"}},"vegan":{"type":"boolean"}},"required":["item","price"]}},"owner":{"type":"object","properties":{"name":{"type":"string"},"email":{"type":"null"}},"required":["name","email"]}},"required":["shop","open","rating","menu","owner"]}
[exit 0]
```

Without `--compact` the same schema is printed indented.

## diff

Compares two documents by structure: `+` added, `-` removed, `~` changed.
Object key order is ignored, arrays are compared by index, and `true` is not
equal to `1`. `shop2.json` is `shop.json` with a few edits.

```
$ jsonlens diff shop.json shop2.json
~ open: true -> false
~ menu[0].price: 3 -> 3.5
- menu[2]: {"item":"Croissant","price":3.25,"vegan":false}
~ owner.email: null -> "maria@example.com"
+ wifi: "cafe-guest"
5 differences
[exit 1]
```

Options: `--json` (machine-readable), `-q` (exit code only).

## Errors and exit codes

```
$ jsonlens get bad.json a
jsonlens: error: bad.json: invalid JSON at line 1, column 9: Expecting property name enclosed in double quotes
[exit 2]
```

| Code | Meaning |
| ---- | ------- |
| 0 | Success (for `diff`: documents are identical) |
| 1 | `get` found no match, or `diff` found differences |
| 2 | Error: missing file, invalid JSON, bad path, bad usage |

## Development

```
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"    # or .venv/bin/pip on Linux/macOS
pytest
```

See [ROADMAP.md](ROADMAP.md) for planned features. MIT licensed.
