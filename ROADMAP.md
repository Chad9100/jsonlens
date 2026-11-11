# Roadmap

Ideas for future versions, roughly in priority order.

1. **Filter expressions in paths**, e.g. `users[?(@.age > 30)].name`, so
   `get` can select by value and not only by position or name.
2. **Recursive descent** (`..name`) to find a key at any depth.
3. **Schema output improvements**: string `format` detection (dates, emails,
   UUIDs), `enum` for low-cardinality strings, and min/max for numbers.
4. **Colored diff and tree output** with automatic detection of a terminal,
   plus `--no-color`.
5. **Array diff by key** (`diff --key id`) so reordered records of objects
   are matched by identity instead of by index.
6. **JSON Lines support everywhere**, not only in `schema`: `get`, `tree`
   and `diff` over each record of a `.jsonl` file.
7. **Output formats for `get`**: CSV and TSV for lists of flat objects.
8. **Validate against a schema** (`jsonlens validate FILE SCHEMA`) reusing
   the schema file that `schema` writes.
9. **Streaming for very large files** so `tree` and `schema` do not need the
   whole document in memory.
