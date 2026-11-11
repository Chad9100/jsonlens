import pytest

from jsonlens.errors import JsonLensError
from jsonlens.paths import Descend, Wild, parse_path, query

DOC = {
    "name": "shop",
    "owner": {"name": "Maria"},
    "menu": [
        {"item": "Espresso", "name": "e", "opts": {"name": "small"}},
        {"item": "Tea"},
    ],
}


def test_parse_descend_key():
    assert parse_path("..name") == [Descend, "name"]
    assert parse_path("$..name") == [Descend, "name"]
    assert parse_path("a..b.c") == ["a", Descend, "b", "c"]


def test_parse_descend_wild_and_bracket():
    assert parse_path("..*") == [Descend, Wild]
    assert parse_path("a..[0]") == ["a", Descend, 0]
    assert parse_path('..["x.y"]') == [Descend, "x.y"]


@pytest.mark.parametrize("bad", ["..", "a..", "a...b"])
def test_parse_descend_errors(bad):
    with pytest.raises(JsonLensError):
        parse_path(bad)


def test_descend_finds_key_at_every_depth_in_document_order():
    found = query(DOC, parse_path("..name"))
    assert [v for _, v in found] == ["shop", "Maria", "e", "small"]
    assert found[3][0] == ["menu", 0, "opts", "name"]


def test_descend_after_prefix_only_searches_subtree():
    found = query(DOC, parse_path("menu..name"))
    assert [v for _, v in found] == ["e", "small"]


def test_descend_wildcard_lists_all_descendants():
    found = query({"a": [1, {"b": 2}]}, parse_path("..*"))
    assert [t for t, _ in found] == [["a"], ["a", 0], ["a", 1], ["a", 1, "b"]]


def test_descend_then_index():
    found = query({"a": [[1, 2], [3]]}, parse_path("..[0]"))
    assert [v for _, v in found] == [[1, 2], 1, 3]


def test_descend_no_match():
    assert query(DOC, parse_path("..missing")) == []


def test_cli_descend_collects_list(run, write):
    code, out, _ = run("get", write("d.json", DOC), "..name", "--compact")
    assert code == 0 and out.strip() == '["shop","Maria","e","small"]'


def test_cli_descend_single_match_still_a_list(run, write):
    code, out, _ = run("get", write("d.json", DOC), "..item", "--compact")
    assert out.strip() == '["Espresso","Tea"]'


def test_cli_descend_paths(run, write):
    code, out, _ = run("get", write("d.json", DOC), "..item", "--paths")
    assert out.splitlines() == ["menu[0].item = \"Espresso\"", "menu[1].item = \"Tea\""]


def test_cli_descend_no_match_exit_1(run, write):
    code, _, err = run("get", write("d.json", DOC), "..nope")
    assert code == 1 and "no match" in err
