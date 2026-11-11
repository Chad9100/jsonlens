import json

import pytest

from jsonlens.errors import JsonLensError
from jsonlens.paths import Wild, format_path, parse_path, query

DOC = {
    "name": "demo",
    "users": [
        {"id": 1, "name": "Ann", "tags": ["a", "b"]},
        {"id": 2, "name": "Bob", "tags": []},
        {"id": 3, "name": "Cy"},
    ],
    "config": {"debug": True, "level": 3, "a.b": "dotted"},
}


# --- parsing -----------------------------------------------------------


def test_parse_dotted():
    assert parse_path("a.b.c") == ["a", "b", "c"]


def test_parse_leading_dollar():
    assert parse_path("$.a[0]") == ["a", 0]


def test_parse_root():
    assert parse_path("$") == []
    assert parse_path("") == []


def test_parse_bracket_index_and_negative():
    assert parse_path("a[0][-2]") == ["a", 0, -2]


def test_parse_wildcards():
    assert parse_path("a[*].b.*") == ["a", Wild, "b", Wild]


def test_parse_quoted_key():
    assert parse_path('config["a.b"]') == ["config", "a.b"]


def test_parse_quoted_star_is_literal():
    assert parse_path('["*"]') == ["*"]


def test_parse_leading_bracket():
    assert parse_path("[0].x") == [0, "x"]


@pytest.mark.parametrize("bad", ["a..b", "a.", "a[", "a[x]", "a[1", "a[0]b", 'a["x]'])
def test_parse_errors(bad):
    with pytest.raises(JsonLensError, match="bad path"):
        parse_path(bad)


def test_format_roundtrip():
    for text in ["a.b[0].c", 'x["a.b"]', "[1][2]", "$"]:
        assert format_path(parse_path(text)) == text


# --- querying ----------------------------------------------------------


def test_query_simple():
    assert query(DOC, parse_path("name")) == [(["name"], "demo")]


def test_query_nested_index():
    assert query(DOC, parse_path("users[1].name"))[0][1] == "Bob"


def test_query_negative_index_normalised():
    (trail, value), = query(DOC, parse_path("users[-1].name"))
    assert value == "Cy" and trail == ["users", 2, "name"]


def test_query_wildcard_list():
    values = [v for _, v in query(DOC, parse_path("users[*].id"))]
    assert values == [1, 2, 3]


def test_query_wildcard_skips_missing():
    values = [v for _, v in query(DOC, parse_path("users[*].tags"))]
    assert values == [["a", "b"], []]


def test_query_object_wildcard():
    values = [v for _, v in query(DOC, parse_path("config.*"))]
    assert values == [True, 3, "dotted"]


def test_query_out_of_range_and_missing():
    assert query(DOC, parse_path("users[9]")) == []
    assert query(DOC, parse_path("nope.x")) == []


def test_query_type_mismatch():
    assert query(DOC, parse_path("name[0]")) == []
    assert query(DOC, parse_path("users.name")) == []


def test_query_falsey_values_found():
    assert query({"a": None}, parse_path("a")) == [(["a"], None)]
    assert query({"a": 0}, parse_path("a")) == [(["a"], 0)]


# --- CLI ---------------------------------------------------------------


def test_cli_scalar_string(run, write):
    code, out, _ = run("get", write("d.json", DOC), "name")
    assert code == 0 and out.strip() == '"demo"'


def test_cli_raw_string(run, write):
    code, out, _ = run("get", write("d.json", DOC), "name", "--raw")
    assert out.strip() == "demo"


def test_cli_object_pretty(run, write):
    code, out, _ = run("get", write("d.json", DOC), "config")
    assert json.loads(out) == DOC["config"]
    assert "\n" in out.strip()


def test_cli_wildcard_prints_array(run, write):
    code, out, _ = run("get", write("d.json", DOC), "users[*].name", "--compact")
    assert code == 0 and out.strip() == '["Ann","Bob","Cy"]'


def test_cli_paths_mode(run, write):
    code, out, _ = run("get", write("d.json", DOC), "users[*].id", "--paths")
    assert out.splitlines() == ["users[0].id = 1", "users[1].id = 2", "users[2].id = 3"]


def test_cli_wildcard_raw_lines(run, write):
    code, out, _ = run("get", write("d.json", DOC), "users[*].name", "--raw")
    assert out.splitlines() == ["Ann", "Bob", "Cy"]


def test_cli_no_match_exit_1(run, write):
    code, out, err = run("get", write("d.json", DOC), "users[9]")
    assert code == 1 and out == "" and "no match" in err


def test_cli_bad_path_exit_2(run, write):
    code, _, err = run("get", write("d.json", DOC), "a..b")
    assert code == 2 and "bad path" in err


def test_cli_bad_file_exit_2(run):
    code, _, err = run("get", "missing.json", "a")
    assert code == 2 and "file not found" in err


def test_cli_stdin(run, stdin):
    stdin('{"a": {"b": [10, 20]}}')
    code, out, _ = run("get", "-", "a.b[1]")
    assert code == 0 and out.strip() == "20"


def test_cli_bom_file(run, write):
    code, out, _ = run("get", write("b.json", b'\xef\xbb\xbf{"k": 5}'), "k")
    assert code == 0 and out.strip() == "5"


def test_cli_unicode_output(run, write):
    code, out, _ = run("get", write("u.json", {"n": "café"}), "n", "--raw")
    assert out.strip() == "café"


def test_cli_no_command_exit_2(run):
    code, _, err = run()
    assert code == 2 and "usage" in err
