"""`skynet publish` / `withdraw`: additive Authentik reconcile, undo of only what this run made,
and a delete path that needs git to have let go first."""

from pathlib import Path
from typing import Any

import pytest

from skynet import deploy, publish
from skynet.publish import Route
from skynet.writepath import Ledger, WriteError

TOKEN = "tok-do-not-print"
FLOWS = {"authorization_flow": "auth-flow", "invalidation_flow": "inval-flow"}


class FakeAuthentik:
    def __init__(self) -> None:
        self.providers: list[dict[str, Any]] = [
            {"pk": 1, "mode": "forward_single", "external_host": "https://calibre.aliammar.net", **FLOWS}]
        self.applications: list[dict[str, Any]] = [{"slug": "calibre", "provider": 1}]
        self.outpost: dict[str, Any] = {"pk": "op", "managed": publish.EMBEDDED_OUTPOST, "providers": [1, 7]}
        self.writes: list[tuple[str, str]] = []
        self.fail_on: str | None = None

    def call(self, method: str, path: str, body: Any = None) -> Any:
        if method != "GET":
            self.writes.append((method, path))
        if self.fail_on == f"{method} {path}":
            raise WriteError(f"Authentik refused {method} {path}")
        if method == "GET":
            rows = {"/providers/proxy/?page_size=1000": self.providers,
                    "/core/applications/?page_size=1000": self.applications,
                    "/outposts/instances/?page_size=1000": [self.outpost]}[path]
            return {"results": rows, "pagination": {"next": 0}}
        if method == "POST" and path == "/providers/proxy/":
            row = {"pk": 50 + len(self.providers), **body}
            self.providers.append(row)
            return row
        if method == "POST" and path == "/core/applications/":
            self.applications.append(body)
            return body
        if method == "PATCH":
            self.outpost["providers"] = body["providers"]
            return self.outpost
        if method == "DELETE" and path.startswith("/providers/proxy/"):
            pk = int(path.split("/")[3])
            self.providers = [p for p in self.providers if p["pk"] != pk]
        elif method == "DELETE" and path.startswith("/core/applications/"):
            slug = path.split("/")[3]
            self.applications = [a for a in self.applications if a["slug"] != slug]
        return None


@pytest.fixture
def lab(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    fake = FakeAuthentik()
    state: dict[str, Any] = {"authentik": fake, "routes": [], "probe_fail": False, "converged": True}
    monkeypatch.setattr(deploy, "fetch", lambda repo: None)
    monkeypatch.setattr(deploy, "resolve", lambda repo, ref: "a" * 40)
    monkeypatch.setattr(publish, "service_routes", lambda repo, service: state["routes"])
    monkeypatch.setattr(publish, "authentik_credentials",
                        lambda path=None: {"AUTHENTIK_URL": "http://10.10.80.37:9000", "AUTHENTIK_TOKEN": TOKEN})
    monkeypatch.setattr(publish.Authentik, "call", lambda self, m, p, b=None: fake.call(m, p, b))
    monkeypatch.setattr(publish, "_public_dns", lambda hosts: {h: "pending tofu apply" for h in hosts})

    def converged(repo: Path, context: str, service: str) -> None:
        if not state["converged"]:
            raise WriteError(f"{service} is not running origin/main; deploy it first")
    monkeypatch.setattr(publish, "_converged", converged)

    def probe(context: str, route: Route) -> dict[str, Any]:
        if state["probe_fail"]:
            raise WriteError("forward-auth route does not redirect to the login")
        return {"vhost": route.vhost, "http_code": 302}
    monkeypatch.setattr(publish, "_probe", probe)
    return state


def _publish(tmp_path: Path, service: str = "books") -> Any:
    return publish.publish(tmp_path, service, context="docker-dmz", ledger=Ledger(tmp_path / "state"))


def test_new_forward_auth_vhost_gets_provider_app_and_binding(lab: dict[str, Any], tmp_path: Path) -> None:
    lab["routes"] = [Route("books.aliammar.net", publish.FORWARD_AUTH, public=True)]
    operation = _publish(tmp_path)
    fake = lab["authentik"]
    assert operation.outcome == "success"
    new = next(p for p in fake.providers if p["external_host"] == "https://books.aliammar.net")
    assert new["authorization_flow"] == "auth-flow" and new["mode"] == "forward_single"
    assert {"slug": "books", "name": "Books", "provider": new["pk"],
            "meta_launch_url": "https://books.aliammar.net"} in fake.applications
    assert fake.outpost["providers"] == [1, 7, new["pk"]]  # existing kept, one added
    assert operation.verification["public_dns"] == {"books.aliammar.net": "pending tofu apply"}


def test_already_published_is_idempotent(lab: dict[str, Any], tmp_path: Path) -> None:
    lab["routes"] = [Route("calibre.aliammar.net", publish.FORWARD_AUTH, public=False)]
    operation = _publish(tmp_path, "calibre")
    assert operation.outcome == "success" and lab["authentik"].writes == []


def test_own_auth_route_needs_no_authentik(lab: dict[str, Any], tmp_path: Path,
                                           monkeypatch: pytest.MonkeyPatch) -> None:
    lab["routes"] = [Route("notes.aliammar.net", "own-auth/plain", public=False)]
    monkeypatch.setattr(publish, "authentik_credentials", lambda path=None: pytest.fail("no token needed"))
    assert _publish(tmp_path, "notes").outcome == "success"


def test_failed_probe_undoes_only_what_this_run_created(lab: dict[str, Any], tmp_path: Path) -> None:
    lab["routes"] = [Route("books.aliammar.net", publish.FORWARD_AUTH, public=False)]
    lab["probe_fail"] = True
    operation = _publish(tmp_path)
    fake = lab["authentik"]
    assert (operation.outcome, operation.recovery) == ("rolled-back", "rolled-back")
    assert [p["pk"] for p in fake.providers] == [1]
    assert fake.applications == [{"slug": "calibre", "provider": 1}]
    assert fake.outpost["providers"] == [1, 7]


def test_unconverged_front_door_refuses_before_any_write(lab: dict[str, Any], tmp_path: Path) -> None:
    lab["routes"] = [Route("books.aliammar.net", publish.FORWARD_AUTH, public=False)]
    lab["converged"] = False
    operation = _publish(tmp_path)
    assert operation.outcome == "refused" and lab["authentik"].writes == []


def test_undeclared_service_is_refused(lab: dict[str, Any], tmp_path: Path) -> None:
    assert _publish(tmp_path).reason == "no route for the service in the Caddyfile on origin/main"


def test_slug_collision_is_refused_and_undone(lab: dict[str, Any], tmp_path: Path) -> None:
    lab["routes"] = [Route("calibre.other.aliammar.net", publish.FORWARD_AUTH, public=False)]
    operation = _publish(tmp_path)
    assert operation.outcome == "rolled-back"
    assert operation.reason == "application slug already used by another provider"
    assert [p["pk"] for p in lab["authentik"].providers] == [1]


def test_curl_config_quotes_and_keeps_the_token_off_argv() -> None:
    config = publish.curl_config("POST", "http://a/api/v3/x/", TOKEN, {"name": 'q"uote\\'}).decode()
    assert f'header = "Authorization: Bearer {TOKEN}"' in config
    assert 'data = "{\\"name\\": \\"q\\\\\\"uote\\\\\\\\\\"}"' in config


def test_authentik_call_parses_status_and_hides_body(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    def run(args: list[str], **kwargs: Any) -> Any:
        seen.update(args=args, stdin=kwargs["stdin"])
        return type("R", (), {"returncode": 0, "stdout": b'{"detail": "secret-ish"}\n403'})()
    monkeypatch.setattr(deploy, "_run", run)
    client = publish.Authentik("docker-dmz", "http://10.10.80.37:9000", TOKEN)
    with pytest.raises(WriteError, match="^Authentik refused GET /core/applications/$"):
        client.call("GET", "/core/applications/?page_size=1000")
    assert all(TOKEN not in arg for arg in seen["args"]) and TOKEN.encode() in seen["stdin"]
    assert seen["args"][-4:] == [publish.FRONT_DOOR_CONTAINER, "curl", "--config", "-"]


# --- withdraw -----------------------------------------------------------------------------------

class FakeCloudflare:
    zone_id = "zone"

    def __init__(self) -> None:
        self.rows = [{"id": "r1", "type": "CNAME", "name": "books.aliammar.net", "content": "t.cfargotunnel.com",
                      "proxied": True, "ttl": 1}]
        self.fail_delete = False

    def records(self, name: str) -> list[dict[str, Any]]:
        return [row for row in self.rows if row["name"] == name]

    def call(self, method: str, path: str, body: Any = None) -> Any:
        if method == "DELETE":
            if self.fail_delete:
                raise WriteError("Cloudflare refused DELETE")
            self.rows = [row for row in self.rows if not path.endswith(row["id"])]
        elif method == "POST":
            self.rows.append({"id": "r2", **body})


@pytest.fixture
def withdrawal(lab: dict[str, Any], monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, Any]:
    cloudflare = FakeCloudflare()
    lab["cloudflare"] = cloudflare
    lab["declared"] = ([], set())
    lab["authentik"].providers.append({"pk": 9, "mode": "forward_single",
                                       "external_host": "https://books.aliammar.net", **FLOWS})
    lab["authentik"].applications.append({"slug": "books", "provider": 9})
    monkeypatch.setattr(publish, "_cloudflare", lambda: cloudflare)
    monkeypatch.setattr(publish, "declared", lambda root: lab["declared"])
    monkeypatch.setattr(deploy, "checkout", _null_checkout)
    return lab


class _null_checkout:
    def __init__(self, *args: Any) -> None:
        pass

    def __enter__(self) -> Path:
        return Path("/nonexistent")

    def __exit__(self, *args: Any) -> None:
        return None


def _withdraw(tmp_path: Path, confirm: str = "books.aliammar.net") -> Any:
    return publish.withdraw(tmp_path, "books.aliammar.net", confirm, context="docker-dmz",
                            ledger=Ledger(tmp_path / "state"))


def test_withdraw_deletes_leftovers_once_git_lets_go(withdrawal: dict[str, Any], tmp_path: Path) -> None:
    operation = _withdraw(tmp_path)
    assert operation.outcome == "success"
    assert withdrawal["cloudflare"].rows == []
    assert [p["pk"] for p in withdrawal["authentik"].providers] == [1]
    assert operation.verification["deleted"] == ["application:books", "provider:9", "cname:books.aliammar.net"]


def test_withdraw_needs_the_name_repeated(withdrawal: dict[str, Any], tmp_path: Path) -> None:
    operation = _withdraw(tmp_path, confirm="books")
    assert (operation.outcome, operation.code) == ("refused", 2) and withdrawal["cloudflare"].rows


def test_withdraw_refuses_while_git_still_declares_the_vhost(withdrawal: dict[str, Any],
                                                             tmp_path: Path) -> None:
    withdrawal["declared"] = ([], {"books.aliammar.net"})
    operation = _withdraw(tmp_path)
    assert operation.outcome == "refused" and withdrawal["authentik"].writes == []


def test_failed_withdraw_restores_the_public_record(withdrawal: dict[str, Any], tmp_path: Path) -> None:
    cloudflare = withdrawal["cloudflare"]
    cloudflare.fail_delete = True
    operation = _withdraw(tmp_path)
    assert operation.outcome == "failed"  # nothing of Cloudflare's was deleted, so nothing restored
    assert cloudflare.records("books.aliammar.net")
