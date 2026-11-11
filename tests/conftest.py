import io
import json
import sys

import pytest

from jsonlens.cli import main


@pytest.fixture
def write(tmp_path):
    """Write JSON (or raw bytes/str) to a temp file and return its path."""

    def _write(name, content):
        path = tmp_path / name
        if isinstance(content, bytes):
            path.write_bytes(content)
        elif isinstance(content, str):
            path.write_text(content, encoding="utf-8")
        else:
            path.write_text(json.dumps(content), encoding="utf-8")
        return str(path)

    return _write


@pytest.fixture
def run(capsys):
    """Run the CLI, returning (exit_code, stdout, stderr)."""

    def _run(*argv):
        code = main(list(argv))
        out, err = capsys.readouterr()
        return code, out, err

    return _run


@pytest.fixture
def stdin(monkeypatch):
    def _set(data):
        raw = data if isinstance(data, bytes) else data.encode("utf-8")

        class Fake:
            buffer = io.BytesIO(raw)

        monkeypatch.setattr(sys, "stdin", Fake())

    return _set
