"""Shared collector plumbing: one literal credential rule, atomic publication, safe results."""

import io
import json
from pathlib import Path

import pytest

from skynet import common

KEYS = ("HOST", "PASS")


def _file(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "credentials.env"
    path.write_text(text, encoding="utf-8")
    return path


def _refused(path: Path) -> None:
    with pytest.raises(common.CollectionError) as caught:
        common.read_assignments(path, KEYS, KEYS)
    assert caught.value.code == 3


def test_quoted_and_bare_values_parse_literally(tmp_path: Path) -> None:
    path = _file(tmp_path, "# comment\nHOST=a.lab  # trailing\nPASS='$(id);`x`|&'\n")
    assert common.read_assignments(path, KEYS, KEYS) == {"HOST": "a.lab", "PASS": "$(id);`x`|&"}


@pytest.mark.parametrize("text", [
    "HOST=a\nHOST=b\nPASS=p\n",           # duplicate
    "HOST=a\n",                           # required key missing
    "HOST=a\nPASS=p\nOTHER=x\n",          # unknown key
    "HOST=a\nPASS=p\nexport X=1\n",       # not an assignment
    "HOST=a\nPASS=''\n",                  # empty value
    "HOST=a\nPASS='p\x7fq'\n",            # control character
])
def test_malformed_files_are_refused(tmp_path: Path, text: str) -> None:
    _refused(_file(tmp_path, text))


def test_missing_file_is_unavailable(tmp_path: Path) -> None:
    _refused(tmp_path / "absent.env")


def test_caller_error_type_and_subject(tmp_path: Path) -> None:
    class Refused(Exception):
        def __init__(self, reason: str, code: int):
            super().__init__(reason)
            self.code = code

    with pytest.raises(Refused, match="^Arcane credentials unavailable$"):
        common.read_assignments(tmp_path / "absent.env", KEYS, KEYS, error=Refused, service="Arcane")


@pytest.mark.parametrize(("value", "valid"), [
    ("pve.lab", True), ("10.10.50.11", True), ("https://x", False), ("a:8006", False),
    ("user@h", False), ("-h", False),
])
def test_host_contract(value: str, valid: bool) -> None:
    assert common.valid_host(value) is valid


def test_port_contract() -> None:
    assert common.port("8007") == 8007
    for value in ("0", "65536", "x"):
        with pytest.raises(common.CollectionError):
            common.port(value)


def test_publish_replaces_atomically(tmp_path: Path) -> None:
    path = tmp_path / "snapshot.json"
    common.publish_json(path, {"a": 1})
    assert json.loads(path.read_text()) == {"a": 1}
    assert [p.name for p in tmp_path.iterdir()] == ["snapshot.json"]


def test_unserializable_publish_keeps_previous_bytes(tmp_path: Path) -> None:
    path = tmp_path / "snapshot.json"
    path.write_text("previous")
    with pytest.raises(common.CollectionError):
        common.publish_json(path, {"bad": float("nan")})
    assert path.read_text() == "previous"
    assert [p.name for p in tmp_path.iterdir()] == ["snapshot.json"]


def test_run_success_publishes_every_output(tmp_path: Path) -> None:
    outputs = (tmp_path / "a.json", tmp_path / "b.json")
    result = common.run("pair", outputs, lambda: ({"collected": "t", "n": [1]}, {"m": 2}),
                        lambda first, second: {"n": len(first["n"]), "m": second["m"]})
    assert (result.code, result.outcome, result.collected, result.counts) == (0, "success", "t",
                                                                              {"n": 1, "m": 2})
    assert all(path.exists() for path in outputs)


@pytest.mark.parametrize(("code", "outcome"), [(3, "unavailable"), (1, "failure")])
def test_run_failure_publishes_nothing(tmp_path: Path, code: int, outcome: str) -> None:
    def read() -> tuple[dict[str, str], ...]:
        raise common.CollectionError("remote transport unavailable", code)

    output = tmp_path / "a.json"
    result = common.run("x", (output,), read, lambda data: {})
    assert (result.code, result.outcome) == (code, outcome)
    assert result.reason is not None and result.reason.startswith("remote transport unavailable;")
    assert not output.exists()


def test_emit_reports_json_without_counts_on_failure(tmp_path: Path) -> None:
    result = common.Result("x", (tmp_path / "a.json",), 3, "unavailable", reason="r")
    stream = io.StringIO()
    assert common.emit(result, True, stream) == 3
    assert json.loads(stream.getvalue()) == {"target": "x", "output": str(tmp_path / "a.json"),
                                             "outcome": "unavailable", "reason": "r"}
