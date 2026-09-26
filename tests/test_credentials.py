"""Credential files are literal data: shell syntax, duplicates, and gaps fail closed (exit 3)."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from skynet import deployment, dns, omada, opnsense, pbs

CA = "/etc/ssl/certs/ca-certificates.crt"
# module parser, error type, a complete valid file
CASES: dict[str, tuple[Callable[[Path], Any], type[Exception], str]] = {
    "dns": (dns.credentials, dns.CollectionError,
            f"TECH_HOST=dns.lab\nTECH_TOKEN=abc123\nTECH_CACERT={CA}\n"),
    "pbs": (pbs._literal_assignments, pbs.CollectionError,
            "PBS_HOST=pbs.lab\nPBS_TOKEN='root@pam!ro:abc'\n"),
    "opnsense": (opnsense.credentials, opnsense.CollectionError,
                 f"OPN_HOST=fw.lab\nOPN_KEY=key\nOPN_SECRET='c2VjcmV0'\nOPN_CACERT={CA}\n"),
    "omada": (omada.credentials, omada.CollectionError,
              f"OMADA_HOST=omada.lab\nOMADA_USER=ro\nOMADA_PASS=pw\nOMADA_CACERT={CA}\n"),
    "arcane": (deployment.credentials, deployment.VerificationError,
               "ARCANE_URL=https://arcane.lab\nARCANE_TOKEN=abc\n"),
}


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "credentials.env"
    path.write_text(text, encoding="utf-8")
    return path


def _refused(parse: Callable[[Path], Any], error: type[Exception], path: Path) -> None:
    with pytest.raises(error) as caught:
        parse(path)
    assert caught.value.code == 3  # type: ignore[attr-defined]


@pytest.mark.parametrize("name", CASES)
def test_valid_file_parses(name: str, tmp_path: Path) -> None:
    parse, _, valid = CASES[name]
    assert parse(_write(tmp_path, valid))


@pytest.mark.parametrize("name", CASES)
def test_missing_file_is_unavailable(name: str, tmp_path: Path) -> None:
    parse, error, _ = CASES[name]
    _refused(parse, error, tmp_path / "absent.env")


@pytest.mark.parametrize("name", CASES)
def test_duplicate_key_is_refused(name: str, tmp_path: Path) -> None:
    parse, error, valid = CASES[name]
    first = valid.splitlines()[0]
    _refused(parse, error, _write(tmp_path, valid + first + "\n"))


@pytest.mark.parametrize("name", CASES)
def test_required_key_missing_is_refused(name: str, tmp_path: Path) -> None:
    parse, error, valid = CASES[name]
    _refused(parse, error, _write(tmp_path, "\n".join(valid.splitlines()[1:]) + "\n"))


@pytest.mark.parametrize("name", CASES)
def test_non_assignment_line_is_refused(name: str, tmp_path: Path) -> None:
    parse, error, valid = CASES[name]
    _refused(parse, error, _write(tmp_path, valid + "export EVIL=1; rm -rf /\n"))


@pytest.mark.parametrize("name", ["dns", "pbs"])
def test_shell_expansion_in_value_is_refused(name: str, tmp_path: Path) -> None:
    parse, error, valid = CASES[name]
    key = valid.splitlines()[1].split("=", 1)[0]
    _refused(parse, error, _write(tmp_path, valid.replace(f"{key}=", f"{key}=$(id)#", 1)))
