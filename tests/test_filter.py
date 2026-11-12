import pytest

from jsonlens.errors import JsonLensError
from jsonlens.paths import Filter, format_path, has_wildcard, parse_path, query

DOC = {
    "users": [
        {"name": "Ann", "age": 41, "active": True, "tags": ["a"]},
        {"name": "Bob", "age": 25, "active": False},
        {"name": "Cy", "age": 30.5, "active": True, "address": {"city": "Oslo"}},
        {"name": "Di", "age": "n/a"},
    ]
}


def names(path):
    return [v for _, v in query(DOC, parse_path(path))]


def test_parse_filter():
    toks = parse_path("users[?(@.age > 30)].name")
    assert toks == ["users", Filter(["age"], ">", 30), "name"]
    assert has_wildcard(toks)


def test_greater_than_skips_non_numbers():
    assert names("users[?(@.age > 30)].name") == ["Ann", "Cy"]


def test_equality_string_and_bool():
    assert names('users[?(@.name == "Bob")].age') == [25]
    assert names("users[?(@.name == 'Ann')].age") == [41]
    assert names("users[?(@.active == true)].name") == ["Ann", "Cy"]


def test_true_does_not_equal_one():
    assert query({"a": [{"x": 1}, {"x": True}]}, parse_path("a[?(@.x == 1)]")) == [(["a", 0], {"x": 1})]


def test_not_equal_and_missing_key():
    assert names("users[?(@.active != true)].name") == ["Bob"]


def test_existence_and_nested_path():
    assert names("users[?(@.address)].name") == ["Cy"]
    assert names('users[?(@.address.city == "Oslo")].name') == ["Cy"]


def test_without_parens_and_bracket_in_string():
    assert names("users[?@.age <= 25].name") == ["Bob"]
    doc = {"a": [{"k": "x]y"}, {"k": "z"}]}
    assert query(doc, parse_path('a[?(@.k == "x]y")]')) == [(["a", 0], {"k": "x]y"})]


def test_concrete_trail_and_filter_on_dict_values():
    matches = query(DOC, parse_path("users[?(@.age >= 41)]"))
    assert [format_path(t) for t, _ in matches] == ["users[0]"]
    assert query({"m": {"p": {"v": 1}, "q": {"v": 2}}}, parse_path("m[?(@.v == 2)]"))[0][0] == ["m", "q"]


def test_no_match_is_empty():
    assert query(DOC, parse_path("users[?(@.age > 100)]")) == []


@pytest.mark.parametrize(
    "bad",
    ["a[?(age > 3)]", "a[?(@.x > abc)]", "a[?(@.x > 3)", "a[?(@.*.x == 1)]", "a[?(@.x == )]"],
)
def test_bad_filters(bad):
    with pytest.raises(JsonLensError):
        parse_path(bad)
