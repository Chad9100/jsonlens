import json

from jsonlens.schema import infer
from jsonlens.validate import validate


def msgs(value, schema):
    from jsonlens.paths import format_path

    return [(format_path(t), m) for t, m in validate(value, schema)]


def test_inferred_schema_accepts_its_source():
    doc = {"a": [1, 2.5, None], "b": {"c": "x"}}
    assert validate(doc, infer(doc)) == []


def test_type_mismatch():
    assert msgs("x", {"type": "integer"}) == [("$", "expected integer, got string")]


def test_bool_is_not_number():
    assert msgs(True, {"type": "number"})


def test_integer_accepts_whole_float_and_number_accepts_int():
    assert validate(3.0, {"type": "integer"}) == []
    assert validate(3, {"type": "number"}) == []
    assert msgs(3.5, {"type": "integer"})


def test_type_list():
    assert validate(None, {"type": ["string", "null"]}) == []
    assert msgs(1, {"type": ["string", "null"]}) == [
        ("$", "expected string or null, got integer")
    ]


def test_required_and_nested_paths():
    schema = {
        "type": "object",
        "properties": {"u": {"type": "array", "items": {"type": "object",
                    "properties": {"age": {"type": "integer"}}, "required": ["id"]}}},
    }
    result = msgs({"u": [{"id": 1, "age": "x"}, {"age": 2}]}, schema)
    assert result == [
        ("u[0].age", "expected integer, got string"),
        ("u[1]", "missing required key 'id'"),
    ]


def test_enum_min_max_length():
    assert msgs("z", {"enum": ["a", "b"]}) == [("$", 'not one of ["a", "b"]')]
    assert msgs(5, {"minimum": 6}) == [("$", "5 is below minimum 6")]
    assert msgs(5, {"maximum": 4}) == [("$", "5 is above maximum 4")]
    assert msgs("ab", {"minLength": 3})
    assert msgs("abc", {"maxLength": 2})


def test_cli_valid(run, write):
    d = write("d.json", {"a": 1})
    s = write("s.json", {"type": "object", "required": ["a"]})
    code, out, _ = run("validate", d, s)
    assert code == 0 and out.strip() == "valid"


def test_cli_invalid(run, write):
    d = write("d.json", {"a": "x"})
    s = write("s.json", {"properties": {"a": {"type": "integer"}}, "required": ["b"]})
    code, out, _ = run("validate", d, s)
    assert code == 1
    assert "$: missing required key 'b'" in out
    assert "a: expected integer, got string" in out
    assert out.strip().endswith("2 problems")


def test_cli_quiet(run, write):
    d = write("d.json", 1)
    s = write("s.json", {"type": "string"})
    code, out, _ = run("validate", d, s, "-q")
    assert code == 1 and out == ""


def test_cli_stdin_and_roundtrip(run, write, stdin):
    s = write("s.json", json.dumps(infer({"a": [1]})))
    stdin('{"a": ["no"]}')
    code, out, _ = run("validate", "-", s)
    assert code == 1 and "a[0]: expected integer, got string" in out


def test_cli_bad_schema_and_unknown_type(run, write):
    d = write("d.json", 1)
    code, _, err = run("validate", d, write("s.json", [1]))
    assert code == 2 and "schema" in err
    code, _, err = run("validate", d, write("t.json", {"type": "blob"}))
    assert code == 2 and "unknown type" in err


def test_pattern():
    s = {"type": "string", "pattern": "^[a-z]+-\\d+$"}
    assert validate("ab-12", s) == []
    assert msgs("AB", s) == [("$", "does not match pattern '^[a-z]+-\\\\d+$'")]
    assert validate(5, {"pattern": "x"}) == []


def test_bad_pattern_is_an_error(run, write):
    code, _, err = run("validate", write("d.json", '"x"'), write("s.json", {"pattern": "("}))
    assert code == 2 and "bad pattern" in err


def test_additional_properties_false_and_schema():
    s = {"properties": {"a": {}}, "additionalProperties": False}
    assert msgs({"a": 1, "b": 2}, s) == [("b", "additional property not allowed")]
    assert validate({"a": 1}, s) == []
    s2 = {"properties": {"a": {}}, "additionalProperties": {"type": "integer"}}
    assert msgs({"a": "x", "b": "y"}, s2) == [("b", "expected integer, got string")]
    assert validate({"a": "x", "b": 1}, s2) == []


def test_any_of_and_one_of():
    any_s = {"anyOf": [{"type": "string"}, {"type": "integer"}]}
    assert validate(1, any_s) == []
    assert msgs(1.5, any_s) == [("$", "does not match any of the anyOf schemas")]
    one = {"oneOf": [{"type": "integer"}, {"type": "number"}]}
    assert msgs(3, one) == [("$", "matches 2 of the oneOf schemas, expected exactly 1")]
    assert validate(3.5, one) == []
    assert msgs("x", one) == [("$", "does not match any of the oneOf schemas")]


def test_ref_to_definitions_and_recursion():
    s = {
        "type": "object",
        "properties": {"home": {"$ref": "#/definitions/addr"}, "kids": {"type": "array", "items": {"$ref": "#"}}},
        "definitions": {"addr": {"type": "object", "required": ["zip"]}},
    }
    assert validate({"home": {"zip": 1}, "kids": [{}]}, s) == []
    assert msgs({"home": {}, "kids": [{"home": {}}]}, s) == [
        ("home", "missing required key 'zip'"),
        ("kids[0].home", "missing required key 'zip'"),
    ]


def test_bad_ref(run, write):
    d = write("d.json", 1)
    code, _, err = run("validate", d, write("s.json", {"$ref": "#/nope"}))
    assert code == 2 and "cannot resolve" in err
    code, _, err = run("validate", d, write("t.json", {"$ref": "http://x/y"}))
    assert code == 2 and "local" in err


def test_cli_both_stdin(run):
    code, _, err = run("validate", "-", "-")
    assert code == 2
