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


def test_and_or():
    assert names('users[?(@.age > 30 && @.active == true)].name') == ["Ann", "Cy"]
    assert names('users[?(@.age > 40 && @.active == false)].name') == []
    assert names('users[?(@.name == "Bob" || @.name == "Di")].name') == ["Bob", "Di"]


def test_and_binds_tighter_than_or():
    # Bob || (age > 40 && active)  -> Ann, Bob
    assert names('users[?(@.name == "Bob" || @.age > 40 && @.active == true)].name') == ["Ann", "Bob"]


def test_parentheses_around_terms_and_operators_in_strings():
    assert names('users[?((@.age > 30) && (@.address))].name') == ["Cy"]
    doc = {"a": [{"k": "x && y"}, {"k": "z || w"}, {"k": "q"}]}
    assert query(doc, parse_path('a[?(@.k == "x && y" || @.k == "q")]')) == [
        (["a", 0], {"k": "x && y"}),
        (["a", 2], {"k": "q"}),
    ]


def test_grouping_overrides_precedence():
    # without grouping: Ann || (Bob && age > 40)  -> Ann
    assert names('users[?(@.name == "Ann" || @.name == "Bob" && @.age > 40)].name') == ["Ann"]
    # with grouping: (Ann || Bob) && age > 40  -> Ann
    assert names('users[?((@.name == "Bob" || @.name == "Cy") && @.active == true)].name') == ["Cy"]
    assert names('users[?(@.active == true && (@.age > 40 || @.address))].name') == ["Ann", "Cy"]


def test_nested_and_quoted_parentheses():
    assert names('users[?(((@.age > 40 || @.age < 30)) && (@.active == false || @.name == "Ann"))].name') == [
        "Ann",
        "Bob",
    ]
    doc = {"a": [{"k": "(x"}, {"k": "y)"}, {"k": "z"}]}
    got = query(doc, parse_path('a[?((@.k == "(x" || @.k == "y)") && @.k)]'))
    assert [v["k"] for _, v in got] == ["(x", "y)"]


def test_parse_grouped_filter():
    toks = parse_path("a[?((@.x == 1 || @.y == 2) && @.z)]")
    outer = toks[1].groups
    assert len(outer) == 1 and len(outer[0]) == 2
    assert outer[0][0].groups == [[Filter(["x"], "==", 1)], [Filter(["y"], "==", 2)]]
    assert outer[0][1] == Filter(["z"], None, None)


@pytest.mark.parametrize("bad", ["a[?((@.x > 1 ||) && @.y)]", "a[?(() && @.y)]"])
def test_bad_grouped_filters(bad):
    with pytest.raises(JsonLensError):
        parse_path(bad)


def test_regex_match():
    assert names('users[?(@.name =~ "^[AB]")].name') == ["Ann", "Bob"]
    assert names("users[?(@.name =~ 'i$' && @.age == 'n/a')].name") == ["Di"]
    assert names('users[?(@.age =~ "4")].name') == []  # numbers never match


def test_parse_boolean_filter():
    toks = parse_path("a[?(@.x > 1 && @.y == 2 || @.z)]")
    assert has_wildcard(toks)
    assert toks[1].groups == [
        [Filter(["x"], ">", 1), Filter(["y"], "==", 2)],
        [Filter(["z"], None, None)],
    ]


@pytest.mark.parametrize(
    "bad",
    ["a[?(@.x > 1 &&)]", "a[?(@.x =~ 3)]", 'a[?(@.x =~ "(")]', "a[?(@.x > 1 || y)]"],
)
def test_bad_boolean_filters(bad):
    with pytest.raises(JsonLensError):
        parse_path(bad)


@pytest.mark.parametrize(
    "bad",
    ["a[?(age > 3)]", "a[?(@.x > abc)]", "a[?(@.x > 3)", "a[?(@.*.x == 1)]", "a[?(@.x == )]"],
)
def test_bad_filters(bad):
    with pytest.raises(JsonLensError):
        parse_path(bad)
