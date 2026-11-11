import pytest

from jsonlens.errors import JsonLensError
from jsonlens.loader import load, parse


def test_load_plain_file(write):
    assert load(write("a.json", {"a": 1})) == {"a": 1}


def test_load_strips_utf8_bom(write):
    path = write("bom.json", b"\xef\xbb\xbf" + b'{"a": 1}')
    assert load(path) == {"a": 1}


def test_load_unicode(write):
    path = write("u.json", '{"name": "café"}')
    assert load(path)["name"] == "café"


def test_load_stdin(stdin):
    stdin('{"x": [1, 2]}')
    assert load("-") == {"x": [1, 2]}


def test_load_stdin_bom(stdin):
    stdin(b"\xef\xbb\xbf[1]")
    assert load("-") == [1]


def test_missing_file():
    with pytest.raises(JsonLensError, match="file not found"):
        load("definitely-not-here.json")


def test_directory(tmp_path):
    with pytest.raises(JsonLensError):
        load(str(tmp_path))


def test_invalid_json_reports_position(write):
    path = write("bad.json", '{\n  "a": 1,\n  "b": \n}')
    with pytest.raises(JsonLensError, match=r"invalid JSON at line 4, column 1"):
        load(path)


def test_empty_file(write):
    with pytest.raises(JsonLensError, match="empty input"):
        load(write("e.json", "   \n"))


def test_invalid_utf8(write):
    with pytest.raises(JsonLensError, match="not valid UTF-8"):
        load(write("l1.json", b'{"a": "\xe9"}'))


def test_deep_nesting():
    with pytest.raises(JsonLensError, match="nested too deeply"):
        parse("[" * 100000 + "]" * 100000)


def test_scalar_root_is_fine(write):
    assert load(write("s.json", "42")) == 42
