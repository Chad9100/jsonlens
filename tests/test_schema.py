import json

import pytest

from jsonlens.schema import infer, infer_many


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, "null"),
        (True, "boolean"),
        (3, "integer"),
        (3.5, "number"),
        ("x", "string"),
    ],
)
def test_scalar_types(value, expected):
    assert infer(value) == {"type": expected}


def test_bool_is_not_integer():
    assert infer([True, 1]) == {"type": "array", "items": {"type": ["boolean", "integer"]}}


def test_object_properties_and_required():
    assert infer({"a": 1, "b": "x"}) == {
        "type": "object",
        "properties": {"a": {"type": "integer"}, "b": {"type": "string"}},
        "required": ["a", "b"],
    }


def test_empty_object_and_array():
    assert infer({}) == {"type": "object", "properties": {}}
    assert infer([]) == {"type": "array"}


def test_array_items_merge_objects_and_optional_keys():
    schema = infer([{"id": 1, "name": "a"}, {"id": 2}])
    items = schema["items"]
    assert items["required"] == ["id"]
    assert set(items["properties"]) == {"id", "name"}


def test_mixed_types_listed_sorted():
    assert infer([1, "a", None])["items"]["type"] == ["integer", "null", "string"]


def test_integer_and_float_merge_to_number():
    assert infer([1, 2.5])["items"] == {"type": "number"}


def test_nested_arrays():
    assert infer([[1], [2, 3]])["items"] == {"type": "array", "items": {"type": "integer"}}


def test_nullable_property():
    schema = infer([{"a": 1}, {"a": None}])
    assert schema["items"]["properties"]["a"] == {"type": ["integer", "null"]}


def test_object_and_scalar_union():
    schema = infer([{"a": 1}, 5])["items"]
    assert schema["type"] == ["integer", "object"]
    assert schema["properties"]["a"] == {"type": "integer"}


def test_infer_many_for_json_lines():
    schema = infer_many([{"a": 1}, {"a": 2, "b": True}])
    assert schema["required"] == ["a"]
    assert schema["properties"]["b"] == {"type": "boolean"}


def test_key_order_preserved():
    assert list(infer({"z": 1, "a": 2})["properties"]) == ["z", "a"]


def test_cli_schema(run, write):
    code, out, _ = run("schema", write("d.json", {"a": [1, 2]}), "--compact")
    assert code == 0
    assert json.loads(out) == {
        "type": "object",
        "properties": {"a": {"type": "array", "items": {"type": "integer"}}},
        "required": ["a"],
    }


def test_cli_schema_stdin(run, stdin):
    stdin('"hello"')
    code, out, _ = run("schema", "-")
    assert json.loads(out) == {"type": "string"}


def test_cli_schema_lines(run, write):
    path = write("l.jsonl", '{"a": 1}\n\n{"a": 2, "b": "x"}\n')
    code, out, _ = run("schema", path, "--lines")
    schema = json.loads(out)
    assert code == 0 and schema["required"] == ["a"]


def test_cli_schema_lines_bad_line(run, write):
    path = write("l.jsonl", '{"a": 1}\n{oops}\n')
    code, _, err = run("schema", path, "--lines")
    assert code == 2 and ":2: invalid JSON" in err


def test_cli_schema_invalid(run, write):
    code, _, err = run("schema", write("d.json", "[1,"))
    assert code == 2 and "invalid JSON" in err
