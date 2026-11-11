import json

from jsonlens.diff import diff, format_change


def kinds(a, b):
    return [(k, ".".join(map(str, t)), o, n) for k, t, o, n in diff(a, b)]


def test_identical():
    assert diff({"a": [1, {"b": 2}]}, {"a": [1, {"b": 2}]}) == []


def test_changed_scalar():
    assert kinds({"a": 1}, {"a": 2}) == [("changed", "a", 1, 2)]


def test_added_and_removed_keys():
    result = kinds({"a": 1, "b": 2}, {"a": 1, "c": 3})
    assert ("removed", "b", 2, None) in result
    assert ("added", "c", None, 3) in result
    assert len(result) == 2


def test_nested_path():
    assert kinds({"a": {"b": {"c": 1}}}, {"a": {"b": {"c": 2}}}) == [("changed", "a.b.c", 1, 2)]


def test_list_extra_elements():
    assert kinds([1, 2], [1, 2, 3]) == [("added", "2", None, 3)]
    assert kinds([1, 2, 3], [1]) == [("removed", "1", 2, None), ("removed", "2", 3, None)]


def test_list_element_changed():
    assert kinds({"x": [1, 2]}, {"x": [1, 9]}) == [("changed", "x.1", 2, 9)]


def test_type_change():
    assert kinds({"a": 1}, {"a": "1"}) == [("changed", "a", 1, "1")]
    assert kinds({"a": [1]}, {"a": {"0": 1}})[0][0] == "changed"


def test_bool_is_not_int():
    assert kinds({"a": True}, {"a": 1}) == [("changed", "a", True, 1)]


def test_int_equals_float():
    assert diff({"a": 1}, {"a": 1.0}) == []


def test_null_vs_missing():
    assert kinds({"a": None}, {}) == [("removed", "a", None, None)]


def test_key_order_irrelevant():
    assert diff({"a": 1, "b": 2}, {"b": 2, "a": 1}) == []


def test_root_scalars():
    assert kinds(1, 2) == [("changed", "", 1, 2)]


def test_format_lines():
    assert format_change(("added", ["a", 0], None, "x")) == '+ a[0]: "x"'
    assert format_change(("removed", ["k"], 1, None)) == "- k: 1"
    assert format_change(("changed", ["a b"], 1, 2)) == '~ ["a b"]: 1 -> 2'
    assert format_change(("changed", [], 1, 2)) == "~ $: 1 -> 2"


def test_format_truncates_long_values():
    line = format_change(("added", ["k"], None, "x" * 200))
    assert len(line) < 100 and line.endswith("…")


def test_cli_identical_exit_0(run, write):
    code, out, _ = run("diff", write("a.json", {"a": 1}), write("b.json", {"a": 1}))
    assert code == 0 and out == ""


def test_cli_differences_exit_1(run, write):
    code, out, _ = run("diff", write("a.json", {"a": 1}), write("b.json", {"a": 2, "b": 1}))
    assert code == 1
    assert out.splitlines() == ["~ a: 1 -> 2", "+ b: 1", "2 differences"]


def test_cli_single_difference_wording(run, write):
    code, out, _ = run("diff", write("a.json", [1]), write("b.json", [2]))
    assert out.splitlines()[-1] == "1 difference"


def test_cli_json_output(run, write):
    code, out, _ = run("diff", write("a.json", {"a": 1}), write("b.json", {"a": 2}), "--json")
    assert code == 1
    assert json.loads(out) == [{"change": "changed", "path": "a", "old": 1, "new": 2}]


def test_cli_quiet(run, write):
    code, out, _ = run("diff", write("a.json", 1), write("b.json", 2), "-q")
    assert code == 1 and out == ""


def test_cli_stdin_as_first(run, write, stdin):
    stdin('{"a": 1}')
    code, out, _ = run("diff", "-", write("b.json", {"a": 1}))
    assert code == 0


def test_cli_both_stdin_rejected(run):
    code, _, err = run("diff", "-", "-")
    assert code == 2 and "stdin" in err


def test_cli_bad_input_exit_2(run, write):
    code, _, err = run("diff", write("a.json", "{"), write("b.json", {}))
    assert code == 2 and "invalid JSON" in err


def test_cli_missing_file_exit_2(run, write):
    code, _, err = run("diff", write("a.json", {}), "nope.json")
    assert code == 2 and "file not found" in err
