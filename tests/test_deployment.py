"""Deployment verification: nothing partial, stale, stray, or unhealthy reads as verified (F1, F2)."""

from pathlib import Path
from typing import Any

import pytest

from skynet import deployment
from skynet.deployment import VerificationError

REV = "a" * 40


def _row(service: str = "web", *, project: str = "demo", revision: str = REV, status: str = "running",
         health: str | None = "healthy") -> dict[str, Any]:
    state: dict[str, Any] = {"Status": status, "Restarting": False}
    if health is not None:
        state["Health"] = {"Status": health}
    labels = {deployment.PROJECT_LABEL: project, deployment.SERVICE_LABEL: service,
              deployment.REVISION_LABEL: revision}
    return {"Config": {"Labels": labels}, "State": state}


def test_complete_healthy_set_at_the_revision_verifies() -> None:
    evidence = deployment.check_containers([_row("web"), _row("db")], "demo", REV, ["web", "db"])
    assert evidence == {"container_count": 2, "services": ["db", "web"]}


@pytest.mark.parametrize(("rows", "reason"), [
    ([], "no containers observed for the project"),
    ([_row("web")], "expected service has no container"),
    ([_row("web"), _row("db"), _row("old")], "stray container in the project"),
    ([_row("web", revision="b" * 40), _row("db")], "container revision mismatch"),
    ([_row("web", status="exited"), _row("db")], "container is not running"),
    ([_row("web", health="starting"), _row("db")], "container is not healthy"),
    ([_row("web", health=None), _row("db")], "container has no healthcheck"),
    ([_row("web", project="other"), _row("db")], "Docker project identity mismatch"),
])
def test_incomplete_evidence_is_never_healthy(rows: list[dict[str, Any]], reason: str) -> None:
    with pytest.raises(VerificationError, match=f"^{reason}$"):
        deployment.check_containers(rows, "demo", REV, ["web", "db"])


def test_empty_expected_set_is_refused() -> None:
    with pytest.raises(VerificationError) as caught:
        deployment.check_containers([_row()], "demo", REV, [])
    assert caught.value.code == 2


def test_malformed_container_is_unavailable() -> None:
    with pytest.raises(VerificationError) as caught:
        deployment.check_containers([{"Config": {}}], "demo", REV, ["web"])
    assert caught.value.code == 3


def test_running_revision_is_single_or_none() -> None:
    assert deployment.running_revision([_row(), _row("db")]) == REV
    assert deployment.running_revision([_row(), _row("db", revision="b" * 40)]) is None
    assert deployment.running_revision([]) is None
    assert deployment.running_revision([_row(revision="not-a-sha")]) is None


@pytest.mark.parametrize(("service", "revision", "context"), [
    ("demo", "abc123", "docker-dmz"),
    ("../etc", REV, "docker-dmz"),
    ("demo", REV, "-H evil"),
])
def test_invalid_request_is_a_usage_failure(service: str, revision: str, context: str,
                                            tmp_path: Path) -> None:
    with pytest.raises(VerificationError) as caught:
        deployment.verify(service, revision, ["web"], tmp_path, context=context)
    assert caught.value.code == 2


def test_docker_unavailable_is_unavailable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def refuse(*_: Any, **__: Any) -> Any:
        raise OSError
    monkeypatch.setattr(deployment.subprocess, "run", refuse)
    with pytest.raises(VerificationError) as caught:
        deployment.verify("demo", REV, ["web"], tmp_path)
    assert caught.value.code == 3


def test_routes_for_the_service_come_from_the_checkout(repo_copy: Path) -> None:
    assert deployment.route_vhosts(repo_copy, "calibre") == ["calibre.aliammar.net"]
    assert deployment.route_vhosts(repo_copy, "no-such-service") == []


def test_missing_route_source_is_unavailable(tmp_path: Path) -> None:
    with pytest.raises(VerificationError) as caught:
        deployment.route_vhosts(tmp_path, "calibre")
    assert caught.value.code == 3
