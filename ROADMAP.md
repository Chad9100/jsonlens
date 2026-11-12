# Roadmap

Ideas for future versions, roughly in priority order. (Done: recursive
descent `..name`, filter expressions `[?(@.age > 30)]` (single comparison), `diff --key`, `get --format csv|tsv`, `validate`, validate `pattern`/`oneOf`/`anyOf`/
`additionalProperties`/local `$ref`.)

1. **Richer filters**: `&&` / `||` and regex matching inside `[?(...)]`.
2. **Schema output improvements**: string `format` detection (dates, emails,
   UUIDs), `enum` for low-cardinality strings, and min/max for numbers.
3. **Colored diff and tree output** with automatic detection of a terminal,
   plus `--no-color`.
4. **JSON Lines support everywhere**, not only in `schema`: `get`, `tree`
   and `diff` over each record of a `.jsonl` file.
5. **More validate keywords**: `format`, `allOf`/`not`, `minItems`/`maxItems`,
   `uniqueItems`, `patternProperties`, remote `$ref`.
6. **Streaming for very large files** so `tree` and `schema` do not need the
   whole document in memory.
