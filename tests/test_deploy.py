"""`skynet deploy`: env and compose go live together at one revision, and a failed deploy returns
to the last verified revision without a human (F2, F13)."""

import dataclasses
import io
import json
import os
import subprocess
import tarfile
from pathlib import Path
from typing import Any

import pytest

from skynet import deploy
from skynet.deploy import HostFacts, Release
from skynet.writepath import Ledger, WriteError

OLD, NEW, OTHER = "1" * 40, "2" * 40, "3" * 40
SECRET = "hunter2-do-not-print"


class FakeHost:
    """One Docker host: what runs, its facts, and which revisions break where."""

    def __init__(self) -> None:
        self.running: dict[str, str | None] = {"demo": OLD, "other": OLD}
        self.facts: dict[str, HostFacts] = {"demo": HostFacts(verified=OLD), "other": HostFacts(verified=OLD)}
        self.main = {"demo": NEW, "other": OLD}
        self.merged = {OLD, NEW, OTHER}
        self.bad_pull: set[str] = set()
        self.bad_up: set[str] = set()
        self.bad_verify: set[str] = set()
        self.pr_error = False
        self.calls: list[tuple[str, ...]] = []


@pytest.fixture
def host(monkeypatch: pytest.MonkeyPatch) -> FakeHost:
    fake = FakeHost()

    def release(repo: Path, service: str, revision: str) -> Release:
        fake.calls.append(("render", service, revision))
        return Release(service, revision, {"name": service, "services": {"web": {}}}, b"")

    def compose(context: str, rel: Release, *verb: str, timeout: float = 0) -> None:
        fake.calls.append((verb[0], rel.service, rel.revision))
        if verb[0] == "pull" and rel.revision in fake.bad_pull:
            raise WriteError("compose pull failed")

    def up(context: str, rel: Release) -> None:
        fake.calls.append(("up", rel.service, rel.revision))
        if rel.revision in fake.bad_up:
            fake.running[rel.service] = None
            raise WriteError("compose up failed")
        fake.running[rel.service] = rel.revision

    def check(repo: Path, context: str, rel: Release) -> dict[str, Any]:
        if rel.revision in fake.bad_verify or fake.running[rel.service] != rel.revision:
            raise WriteError("container is not healthy")
        return {"revision": rel.revision}

    def set_fact(context: str, service: str, name: str, revision: str | None) -> None:
        fake.facts[service] = dataclasses.replace(fake.facts[service], **{name: revision})

    def revert(repo: Path, service: str, failed: str, verified: str, reason: str) -> str:
        fake.calls.append(("revert-pr", service, failed, verified))
        if fake.pr_error:
            raise WriteError("revert push failed")
        return "https://example.invalid/pr/1"

    monkeypatch.setattr(deploy, "fetch", lambda repo: None)
    monkeypatch.setattr(deploy, "resolve", lambda repo, ref: ref)
    monkeypatch.setattr(deploy, "services", lambda repo, ref="": sorted(fake.main))
    monkeypatch.setattr(deploy, "service_revision", lambda repo, service, ref="": fake.main.get(service))
    monkeypatch.setattr(deploy, "merged", lambda repo, revision: revision in fake.merged)
    monkeypatch.setattr(deploy, "manual", lambda repo, service, ref: service == "manual")
    monkeypatch.setattr(deploy, "render", release)
    monkeypatch.setattr(deploy, "compose", compose)
    monkeypatch.setattr(deploy, "stage", lambda context, rel: fake.calls.append(("stage", rel.service, rel.revision)))
    monkeypatch.setattr(deploy, "up", up)
    monkeypatch.setattr(deploy, "check", check)
    monkeypatch.setattr(deploy, "host_facts", lambda context, service: fake.facts[service])
    monkeypatch.setattr(deploy, "set_fact", set_fact)
    monkeypatch.setattr(deploy, "running", lambda context, service: fake.running[service])
    monkeypatch.setattr(deploy, "prune", lambda context, service, keep: [])
    monkeypatch.setattr(deploy, "open_revert_pr", revert)
    return fake


def _deploy(tmp_path: Path, service: str = "demo", revision: str | None = None) -> Any:
    return deploy.deploy(tmp_path, service, revision=revision, context="docker-dmz",
                         ledger=Ledger(tmp_path / "state"))


def test_merged_revision_goes_live_and_becomes_the_rollback_target(host: FakeHost, tmp_path: Path) -> None:
    operation = _deploy(tmp_path)
    assert (operation.outcome, operation.code) == ("success", 0)
    assert host.running["demo"] == NEW and host.facts["demo"].verified == NEW
    order = [call[0] for call in host.calls]
    assert order.index("pull") < order.index("stage") < order.index("up")


def test_bad_image_fails_before_anything_running_changes(host: FakeHost, tmp_path: Path) -> None:
    host.bad_pull.add(NEW)
    operation = _deploy(tmp_path)
    assert operation.outcome == "refused"
    assert "up" not in [call[0] for call in host.calls] and host.running["demo"] == OLD
    assert host.facts["demo"].failed is None  # a transient pull retries on the next tick


@pytest.mark.parametrize("breaks", ["bad_up", "bad_verify"])
def test_failed_deploy_returns_to_verified_and_opens_revert_pr(host: FakeHost, tmp_path: Path,
                                                               breaks: str) -> None:
    getattr(host, breaks).add(NEW)
    operation = _deploy(tmp_path)
    assert (operation.outcome, operation.recovery, operation.code) == ("rolled-back", "rolled-back", 1)
    assert host.running["demo"] == OLD
    assert host.facts["demo"] == HostFacts(verified=OLD, failed=NEW)
    assert ("revert-pr", "demo", NEW, OLD) in host.calls


def test_failed_rollback_is_a_hard_stop(host: FakeHost, tmp_path: Path) -> None:
    host.bad_up.update({NEW, OLD})
    operation = _deploy(tmp_path)
    assert (operation.outcome, operation.code) == ("rollback-failed", 4)
    assert host.facts["demo"].failed == NEW


def test_no_verified_revision_stops_without_a_guess(host: FakeHost, tmp_path: Path) -> None:
    host.facts["demo"] = HostFacts()
    host.bad_verify.add(NEW)
    operation = _deploy(tmp_path)
    assert (operation.outcome, operation.recovery) == ("failed", "no-rollback-target")
    assert host.facts["demo"].failed == NEW


def test_revert_pr_failure_is_reported_not_hidden(host: FakeHost, tmp_path: Path) -> None:
    host.bad_verify.add(NEW)
    host.pr_error = True
    operation = _deploy(tmp_path)
    assert operation.outcome == "rolled-back"
    assert {"step": "revert-pr", "outcome": "failed", "detail": "revert push failed"} in operation.steps


def test_no_revert_pr_when_main_no_longer_holds_the_failure(host: FakeHost, tmp_path: Path) -> None:
    host.bad_verify.add(OTHER)
    operation = _deploy(tmp_path, revision=OTHER)
    assert operation.outcome == "rolled-back"
    assert not [call for call in host.calls if call[0] == "revert-pr"]


def test_unmerged_revision_is_refused_before_rendering(host: FakeHost, tmp_path: Path) -> None:
    unmerged = "4" * 40
    operation = _deploy(tmp_path, revision=unmerged)
    assert (operation.outcome, operation.code) == ("refused", 2)
    assert not [call for call in host.calls if call[0] == "render"]


def test_manual_project_is_refused(host: FakeHost, tmp_path: Path) -> None:
    host.main["manual"] = NEW
    host.running["manual"], host.facts["manual"] = None, HostFacts()
    assert _deploy(tmp_path, "manual").reason == "service is deployed by hand (x-skynet.deploy: manual)"


def test_pending_deploys_only_what_differs_and_holds_failed_revisions(host: FakeHost,
                                                                      tmp_path: Path) -> None:
    results = deploy.pending(tmp_path, context="docker-dmz", ledger=Ledger(tmp_path / "state"))
    assert [(r["target"], r["outcome"]) for r in results] == [("svc/demo", "success")]
    host.main["demo"] = OTHER
    host.bad_verify.add(OTHER)
    first = deploy.pending(tmp_path, context="docker-dmz", ledger=Ledger(tmp_path / "state"))
    assert first[0]["outcome"] == "rolled-back"
    again = deploy.pending(tmp_path, context="docker-dmz", ledger=Ledger(tmp_path / "state"))
    assert again == [{"target": "svc/demo", "source": OTHER, "outcome": "held",
                      "reason": "revision failed and was rolled back; awaiting a new merge"}]
    host.main["demo"] = "5" * 40  # a new merge (the revert or a fix) releases the hold
    host.merged.add("5" * 40)
    assert deploy.pending(tmp_path, context="docker-dmz",
                          ledger=Ledger(tmp_path / "state"))[0]["outcome"] == "success"


# --- render and helpers -------------------------------------------------------------------------

def test_duplicate_env_key_is_refused() -> None:
    with pytest.raises(WriteError, match="more than once"):
        deploy.merge_env("A=1\nB=2\n", "B=secret\n")
    assert deploy.merge_env("A=1", "B=2") == "A=1\nB=2\n"


def test_manual_marker_is_read_from_the_raw_file() -> None:
    assert deploy._MANUAL.search("x-skynet:\n  deploy: manual\nservices: {}\n")
    assert not deploy._MANUAL.search("x-skynet:\n  deploy: auto\nservices:\n  a:\n    deploy: manual\n")


def _archive(files: dict[str, str]) -> bytes:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w") as tar:
        for name, text in files.items():
            info = tarfile.TarInfo(name)
            data = text.encode()
            info.size, info.uid, info.mode = len(data), 1000, 0o664
            tar.addfile(info, io.BytesIO(data))
    return output.getvalue()


def test_release_holds_only_non_secret_files_owned_by_root() -> None:
    archive = _archive({"compose/demo/compose.yaml": "x", "compose/demo/.env.sops": "enc",
                        "compose/demo/.env.git": "A=1", "compose/demo/conf/app.ini": "y"})
    with tarfile.open(fileobj=io.BytesIO(deploy._release_files(archive, "demo"))) as tar:
        members = {m.name: m for m in tar.getmembers()}
    assert sorted(members) == ["compose.yaml", "conf/app.ini"]
    assert all(m.uid == 0 and m.mode == 0o644 for m in members.values())


def test_effect_names_env_keys_but_never_values() -> None:
    old = {"services": {"web": {"image": "a:1", "environment": {"TOKEN": "old-" + SECRET, "KEEP": "x"}}}}
    new = {"services": {"web": {"image": "a:2", "environment": {"TOKEN": SECRET, "NEW": SECRET, "KEEP": "x"},
                                "command": ["run"]}, "db": {"image": "pg:17"}}}
    text = "\n".join(change for _, change in deploy.effect(old, new))
    assert SECRET not in text
    assert "image: `a:1` → `a:2`" in text and "env added: NEW" in text and "env changed: TOKEN" in text
    assert "settings changed: command" in text and "added: `pg:17`" in text


def test_host_facts_parse_only_well_formed_values(monkeypatch: pytest.MonkeyPatch) -> None:
    output = (f"verified={OLD}\nfailed=garbage\nrelease=200 {NEW}\nrelease=100 {OLD}\n"
              f"release=300 {OLD}.tmp\n")
    monkeypatch.setattr(deploy, "_host", lambda *a, **k: output)
    assert deploy.host_facts("docker-dmz", "demo") == HostFacts(OLD, None, ((200, NEW), (100, OLD)))


def test_prune_keeps_newest_verified_and_running(monkeypatch: pytest.MonkeyPatch) -> None:
    releases = tuple((100 - i, f"{i:040x}") for i in range(8))
    removed: list[str] = []
    monkeypatch.setattr(deploy, "host_facts", lambda c, s: HostFacts(releases=releases))
    monkeypatch.setattr(deploy, "_host", lambda c, script, service, *names, **k: removed.extend(names) or "")
    keep = {releases[7][1]}
    assert deploy.prune("docker-dmz", "demo", keep) == [releases[5][1], releases[6][1]]
    assert removed == [releases[5][1], releases[6][1]]


def test_set_fact_refuses_non_revisions() -> None:
    with pytest.raises(WriteError):
        deploy.set_fact("docker-dmz", "demo", "verified", "; rm -rf /")
    with pytest.raises(WriteError):
        deploy.set_fact("docker-dmz", "demo", "../x", OLD)


@pytest.fixture
def git_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    project = repo / "compose" / "demo"
    project.mkdir(parents=True)
    (project / "compose.yaml").write_text("name: demo\nservices:\n  web:\n    image: a:1\n    env_file: .env\n")
    (project / ".env.git").write_text("PLAIN=1\n")
    (project / ".env.sops").write_text("ENCRYPTED\n")
    (project / "app.ini").write_text("config\n")
    for args in (["init", "-q"], ["add", "-A"],
                 ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"]):
        subprocess.run(["git", "-C", str(repo), *args], check=True)
    revision = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True,
                              capture_output=True, text=True).stdout.strip()
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    return repo, revision


def test_render_keeps_secrets_in_a_private_tmpfs_file_and_off_argv(
        git_repo: tuple[Path, str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo, revision = git_repo
    seen: dict[str, Any] = {}
    real_ok = deploy._ok

    def fake_ok(args: list[str], reason: str, code: int = 3, **kwargs: Any) -> bytes:
        if args[:2] != ["docker", "compose"]:
            return real_ok(args, reason, code, **kwargs)
        env_file = kwargs["cwd"] / ".env"
        seen.update(argv=args, mode=os.stat(env_file).st_mode & 0o777, env=env_file.read_text(),
                    cwd=kwargs["cwd"], docker_env=kwargs["env"])
        return json.dumps({"name": "demo", "services": {"web": {
            "image": "a:1", "environment": {"PLAIN": "1", "TOKEN": SECRET}}}}).encode()

    monkeypatch.setattr(deploy, "_ok", fake_ok)
    monkeypatch.setattr(deploy, "_decrypt", lambda encrypted: f"TOKEN={SECRET}\n")
    monkeypatch.setenv("COMPOSE_PROFILES", "evil")
    release = deploy.render(repo, "demo", revision)
    assert seen["mode"] == 0o600 and seen["env"] == f"PLAIN=1\nTOKEN={SECRET}\n"
    assert all(SECRET not in arg for arg in seen["argv"]) and "COMPOSE_PROFILES" not in seen["docker_env"]
    assert not seen["cwd"].exists()  # the rendered env is gone once render returns
    assert release.model["services"]["web"]["labels"] == {"skynet.revision": revision, "skynet.service": "demo"}
    assert SECRET not in repr(release)
    with tarfile.open(fileobj=io.BytesIO(release.files)) as tar:
        assert sorted(tar.getnames()) == ["app.ini", "compose.yaml"]


def test_render_refuses_a_project_named_unlike_its_directory(
        git_repo: tuple[Path, str], monkeypatch: pytest.MonkeyPatch) -> None:
    repo, revision = git_repo
    real_ok = deploy._ok
    monkeypatch.setattr(deploy, "_decrypt", lambda encrypted: "")
    monkeypatch.setattr(deploy, "_ok", lambda args, reason, code=3, **kw: (
        b'{"name": "other", "services": {"web": {}}}' if args[:2] == ["docker", "compose"]
        else real_ok(args, reason, code, **kw)))
    with pytest.raises(WriteError, match="name must match"):
        deploy.render(repo, "demo", revision)


def test_compose_sends_the_model_on_stdin_only(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(deploy, "_ok", lambda args, reason, code=3, **kw: captured.update(args=args, **kw) or b"")
    release = Release("demo", NEW, {"name": "demo", "services": {"web": {"environment": {"T": SECRET}}}}, b"")
    deploy.up("docker-dmz", release)
    assert all(SECRET not in arg for arg in captured["args"]) and SECRET.encode() in captured["stdin"]
    assert captured["args"][captured["args"].index("--project-directory") + 1] == f"{deploy.RELEASES}/demo/{NEW}"
    assert "--wait" in captured["args"] and captured["args"][captured["args"].index("-f") + 1] == "-"


def test_real_git_helpers(git_repo: tuple[Path, str]) -> None:
    repo, revision = git_repo
    assert deploy.services(repo, "HEAD") == ["demo"]
    assert deploy.service_revision(repo, "demo", "HEAD") == revision
    assert deploy.service_revision(repo, "absent", "HEAD") is None
    assert not deploy.manual(repo, "demo", "HEAD")
    with pytest.raises(WriteError):
        deploy.resolve(repo, "--upload-pack=evil")
