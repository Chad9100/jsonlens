DOC = {
    "users": [
        {"id": 1, "name": "Ann, the \"first\"", "tags": ["a", "b"], "active": True},
        {"id": 2, "name": "Bob", "email": None},
    ],
    "names": ["x", "y"],
    "mixed": [1, {"a": 1}],
}


def test_csv_list_of_objects(write, run):
    f = write("d.json", DOC)
    code, out, _ = run("get", f, "users", "--format", "csv")
    assert code == 0
    assert out.splitlines() == [
        "id,name,tags,active,email",
        '1,"Ann, the ""first""","[""a"",""b""]",true,',
        "2,Bob,,,",
    ]


def test_tsv_with_wildcard(write, run):
    f = write("d.json", DOC)
    code, out, _ = run("get", f, "users[*]", "--format", "tsv")
    assert code == 0
    lines = out.splitlines()
    assert lines[0] == "id\tname\ttags\tactive\temail"
    assert lines[2] == "2\tBob\t\t\t"


def test_plain_values_get_value_column(write, run):
    f = write("d.json", DOC)
    code, out, _ = run("get", f, "users[*].id", "--format", "csv")
    assert (code, out) == (0, "value\n1\n2\n")
    code, out, _ = run("get", f, "names", "--format", "tsv")
    assert out == "value\nx\ny\n"


def test_mixed_results_error(write, run):
    f = write("d.json", DOC)
    code, _, err = run("get", f, "mixed", "--format", "csv")
    assert code == 2
    assert "all objects or all plain values" in err


def test_empty_list_error(write, run):
    f = write("d.json", {"a": []})
    code, _, err = run("get", f, "a", "--format", "csv")
    assert code == 2
    assert "empty list" in err


def test_conflicting_flags(write, run):
    f = write("d.json", DOC)
    code, _, err = run("get", f, "names", "--format", "csv", "--raw")
    assert code == 2
    assert "cannot be combined" in err


def test_no_match_still_exit_1(write, run):
    f = write("d.json", DOC)
    code, out, _ = run("get", f, "nope", "--format", "csv")
    assert (code, out) == (1, "")
