from jsonlens.tree import render

DOC = {"name": "demo", "users": [{"id": 1, "tags": ["a"]}, {"id": 2}], "empty": {}, "n": None}


def test_root_scalar():
    assert render(5) == ["$: 5"]


def test_root_object_summary():
    assert render(DOC, depth=0) == ["$ (object, 4 keys) …"]


def test_singular_plural():
    assert render({"a": 1}, depth=0) == ["$ (object, 1 key) …"]
    assert render([1], depth=0) == ["$ (array, 1 item) …"]


def test_empty_container_has_no_ellipsis():
    assert render({}, depth=0) == ["$ (object, 0 keys)"]


def test_depth_one_lists_children_and_marks_truncation():
    lines = render(DOC, depth=1)
    assert lines[0] == "$ (object, 4 keys)"
    assert "├── name: \"demo\"" in lines
    assert "├── users (array, 2 items) …" in lines
    assert "├── empty (object, 0 keys)" in lines
    assert lines[-1] == "└── n: null"
    assert len(lines) == 5


def test_depth_two_expands_one_more_level():
    lines = render(DOC, depth=2)
    assert "│   ├── [0] (object, 2 keys) …" in lines
    assert "│   └── [1] (object, 1 key) …" in lines


def test_depth_three_shows_leaves():
    lines = render(DOC, depth=3)
    assert "│   │   └── tags (array, 1 item) …" in lines
    assert "│   └── [1] (object, 1 key)" in lines
    assert "│       └── id: 2" in lines


def test_max_items_truncates():
    lines = render(list(range(25)), depth=1, max_items=3)
    assert lines[-1] == "└── … 22 more"
    assert len(lines) == 5


def test_leaf_truncation():
    lines = render({"s": "x" * 100}, width=10)
    assert lines[1] == '└── s: "xxxxxxxx…'


def test_ascii_mode():
    lines = render({"a": 1, "b": [1]}, ascii_only=True)
    assert lines[1] == "|-- a: 1"
    assert lines[2] == "`-- b (array, 1 item)"
    assert all(ord(ch) < 128 for line in lines for ch in line)


def test_unicode_keys_kept():
    assert render({"café": 1})[1] == "└── café: 1"


def test_cli_tree(run, write):
    code, out, _ = run("tree", write("d.json", DOC), "--depth", "1")
    assert code == 0 and out.startswith("$ (object, 4 keys)")


def test_cli_tree_stdin(run, stdin):
    stdin("[1, 2]")
    code, out, _ = run("tree", "-")
    assert out.splitlines() == ["$ (array, 2 items)", "├── [0]: 1", "└── [1]: 2"]


def test_cli_negative_depth(run, write):
    code, _, err = run("tree", write("d.json", DOC), "--depth", "-1")
    assert code == 2 and "--depth" in err


def test_cli_bad_max_items(run, write):
    code, _, err = run("tree", write("d.json", DOC), "--max-items", "0")
    assert code == 2


def test_cli_invalid_json(run, write):
    code, _, err = run("tree", write("d.json", "{oops"))
    assert code == 2 and "invalid JSON" in err
