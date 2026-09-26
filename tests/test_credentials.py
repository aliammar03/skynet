"""Credential files are literal data: non-assignments, duplicates, gaps, and control characters
fail closed (exit 3)."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from skynet import dns, omada, opnsense, pbs, proxmox, publish

CA = "/etc/ssl/certs/ca-certificates.crt"
# module parser, error type, a complete valid file
CASES: dict[str, tuple[Callable[[Path], Any], type[Exception], str]] = {
    "dns": (dns.credentials, dns.CollectionError,
            f"TECH_HOST=dns.lab\nTECH_TOKEN=abc123\nTECH_CACERT={CA}\n"),
    "proxmox": (proxmox.credentials, proxmox.CollectionError,
                f"PVE_HOST=pve.lab\nPVE_TOKEN='ro@pve!t=abc'\nPVE_CACERT={CA}\n"),
    "pbs": (pbs.credentials, pbs.CollectionError,
            f"PBS_HOST=pbs.lab\nPBS_TOKEN='root@pam!ro:abc'\nPBS_CACERT={CA}\nPBS_SNI=pbs.lab\n"),
    "opnsense": (opnsense.credentials, opnsense.CollectionError,
                 f"OPN_HOST=fw.lab\nOPN_KEY=key\nOPN_SECRET='c2VjcmV0'\nOPN_CACERT={CA}\n"),
    "omada": (omada.credentials, omada.CollectionError,
              f"OMADA_HOST=omada.lab\nOMADA_USER=ro\nOMADA_PASS=pw\nOMADA_CACERT={CA}\n"),
    "authentik": (publish.authentik_credentials, publish.WriteError,
                  "AUTHENTIK_URL=https://auth.lab\nAUTHENTIK_TOKEN=abc\n"),
    "cloudflare": (publish.cloudflare_credentials, publish.WriteError,
                   "CF_DNS_TOKEN=abc\nCF_ZONE=aliammar.net\nTUNNEL_ID=abc-123\n"),
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


@pytest.mark.parametrize("name", CASES)
def test_control_character_in_value_is_refused(name: str, tmp_path: Path) -> None:
    parse, error, valid = CASES[name]
    key = valid.splitlines()[1].split("=", 1)[0]
    _refused(parse, error, _write(tmp_path, valid.replace(f"{key}=", f"{key}=a\x1bb", 1)))
