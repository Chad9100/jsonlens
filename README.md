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

Filters select array elements (or object values) by value:
`[?(@.field OP literal)]` with `==`, `!=`, `<`, `<=`, `>`, `>=`, or just
`[?(@.field)]` to test that a field exists. The literal is a JSON value
(`30`, `"text"`, `true`, `null`; single-quoted text also works), `@.a.b[0]`
reaches into nested values, and ordering only compares numbers with numbers
and text with text. Remember to quote the path in your shell.

```
$ jsonlens get shop.json 'menu[?(@.price > 3)].item' --compact
["Cold Brew","Croissant"]
[exit 0]

$ jsonlens get shop.json 'menu[?(@.item == "Espresso")].tags' --compact
[["hot","coffee"]]
[exit 0]

$ jsonlens get shop.json 'menu[?(@.vegan == false)]' --paths
menu[2] = {"item":"Croissant","price":3.25,"vegan":false}
[exit 0]
```

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
from), `--compact` (single-line JSON), `--format csv|tsv`.

### CSV and TSV output

`--format csv` (or `tsv`) turns a list of objects into a table. The header is
the union of all keys in first-seen order, missing values and `null` are empty
cells, booleans are `true`/`false`, and nested values are written as compact
JSON. A list of plain values becomes a single `value` column. Mixed results
(objects and scalars together) are an error, and `--format` cannot be combined
with `--paths`, `--raw` or `--compact`.

```
$ jsonlens get shop.json menu --format csv
item,price,tags,vegan
Espresso,3,"[""hot"",""coffee""]",
Cold Brew,4.5,"[""cold""]",
Croissant,3.25,,false
[exit 0]

$ jsonlens get shop.json menu[*] --format tsv
item	price	tags	vegan
Espresso	3	"[""hot"",""coffee""]"	
Cold Brew	4.5	"[""cold""]"	
Croissant	3.25		false
[exit 0]

$ jsonlens get shop.json menu[*].item --format csv
value
Espresso
Cold Brew
Croissant
[exit 0]
```

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

### Matching array elements by key

By default arrays are compared by index, so reordering a list of records
makes everything look changed. `--key FIELD` matches the objects of an array
by the value of `FIELD` instead. With `users.json` and a reordered, edited
`users2.json`:

```
$ jsonlens diff users.json users2.json
~ users[0].id: 1 -> 3
~ users[0].name: "Ann" -> "Cy"
~ users[0].role: "dev" -> "qa"
~ users[1].id: 2 -> 1
~ users[1].name: "Bob" -> "Ann"
~ users[1].role: "ops" -> "lead"
~ users[2].id: 3 -> 4
~ users[2].name: "Cy" -> "Di"
~ users[2].role: "qa" -> "dev"
9 differences
[exit 1]

$ jsonlens diff --key id users.json users2.json
~ users[id=1].role: "dev" -> "lead"
- users[id=2]: {"id":2,"name":"Bob","role":"ops"}
+ users[id=4]: {"id":4,"name":"Di","role":"dev"}
3 differences
[exit 1]
```

An array is matched by key only if every element is an object whose `FIELD`
is a unique string or number, in both documents; otherwise that array falls
back to index comparison.

Options: `--key FIELD`, `--json` (machine-readable), `-q` (exit code only).

## validate

`jsonlens validate FILE SCHEMA` checks a document against a schema file,
such as one written by `jsonlens schema`. Supported keywords: `type` (a name
or a list), `properties`, `required`, `items`, `enum`, `minimum`, `maximum`,
`minLength`, `maxLength`, `pattern` (regex search), `additionalProperties`
(`false` or a schema), `anyOf`, `oneOf` and local `$ref` (`#/definitions/x`,
or `#` for the root); anything else is ignored. Every problem is
reported with its path. Exit code 0 means valid, 1 means problems found.
`-q` prints nothing. `rules.json` is a hand-written schema (price must be a
number, `item` and `price` required) and `bad.json` breaks it.

```
$ jsonlens schema shop.json > s.json
$ jsonlens validate shop.json s.json
valid
[exit 0]

$ jsonlens validate bad.json rules.json
shop: expected string, got integer
menu[0].price: expected number, got string
menu[1]: missing required key 'item'
3 problems
[exit 1]

$ jsonlens validate -q bad.json rules.json
[exit 1]
```

A stricter schema using the newer keywords (`strict.json`: `id` must match
`^[A-Z]-\d+$`, `tag` is a string or an integer, `owner` is a `$ref` to a
definition requiring `name`, no other keys allowed):

```
$ jsonlens validate a.json strict.json
valid
[exit 0]

$ jsonlens validate b.json strict.json
id: does not match pattern '^[A-Z]-\\d+$'
tag: does not match any of the oneOf schemas
owner: missing required key 'name'
extra: additional property not allowed
4 problems
[exit 1]
```

## Errors and exit codes

```
$ jsonlens get bad.json a
jsonlens: error: bad.json: invalid JSON at line 1, column 9: Expecting property name enclosed in double quotes
[exit 2]
```

| Code | Meaning |
| ---- | ------- |
| 0 | Success (for `diff`: documents are identical) |
| 1 | `get` found no match, `diff` found differences, or `validate` found problems |
| 2 | Error: missing file, invalid JSON, bad path, bad usage |

## Development

```
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"    # or .venv/bin/pip on Linux/macOS
pytest
```

See [ROADMAP.md](ROADMAP.md) for planned features. MIT licensed.
