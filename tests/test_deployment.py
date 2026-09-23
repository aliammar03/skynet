"""Deployment verification refuses ambiguous input before any remote observation."""

from pathlib import Path

import pytest

from skynet import deployment


@pytest.mark.parametrize(("service", "revision"), [
    ("whoami", "abc123"),                 # short revision
    ("whoami", "g" * 40),                 # not hex
    ("../etc", "a" * 40),                 # path-like service
    ("", "a" * 40),
])
def test_invalid_request_is_a_usage_failure(service: str, revision: str, tmp_path: Path) -> None:
    report = deployment.verify(service, revision, tmp_path / "unused.env")
    assert report["outcome"] == "failure" and report["exit_code"] == 2


def test_missing_credentials_are_unavailable_not_healthy(tmp_path: Path) -> None:
    report = deployment.verify("whoami", "a" * 40, tmp_path / "absent.env")
    assert report["outcome"] == "unavailable" and report["exit_code"] == 3
