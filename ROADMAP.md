# Roadmap

Ideas for future versions, roughly in priority order. (Done: recursive
descent `..name`, filter expressions `[?(@.age > 30)]`, filter `&&` / `||`
and `=~` regex matching, `diff --key`, `get --format csv|tsv`, `validate`,
validate `pattern`/`oneOf`/`anyOf`/`additionalProperties`/local `$ref`,
validate `minItems`/`maxItems`/`uniqueItems`.)

1. **Schema output improvements**: string `format` detection (dates, emails,
   UUIDs), `enum` for low-cardinality strings, and min/max for numbers.
2. **Colored diff and tree output** with automatic detection of a terminal,
   plus `--no-color`.
3. **JSON Lines support everywhere**, not only in `schema`: `get`, `tree`
   and `diff` over each record of a `.jsonl` file.
4. **More validate keywords**: `format`, `allOf`/`not`, `patternProperties`,
   `minProperties`/`maxProperties`, remote `$ref`.
5. **Streaming for very large files** so `tree` and `schema` do not need the
   whole document in memory.
6. **Parentheses grouping in filters** to override `&&` / `||` precedence.
