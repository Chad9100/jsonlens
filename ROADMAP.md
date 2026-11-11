# Roadmap

Ideas for future versions, roughly in priority order. (Done: recursive
descent `..name`, `diff --key`.)

1. **Filter expressions in paths**, e.g. `users[?(@.age > 30)].name`, so
   `get` can select by value and not only by position or name.
2. **Schema output improvements**: string `format` detection (dates, emails,
   UUIDs), `enum` for low-cardinality strings, and min/max for numbers.
3. **Colored diff and tree output** with automatic detection of a terminal,
   plus `--no-color`.
4. **JSON Lines support everywhere**, not only in `schema`: `get`, `tree`
   and `diff` over each record of a `.jsonl` file.
5. **Output formats for `get`**: CSV and TSV for lists of flat objects.
6. **Validate against a schema** (`jsonlens validate FILE SCHEMA`) reusing
   the schema file that `schema` writes.
7. **Streaming for very large files** so `tree` and `schema` do not need the
   whole document in memory.
