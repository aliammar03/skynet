"""The alert channel never raises into a caller and never leaks credential text."""

from pathlib import Path
from typing import Any

import pytest

from skynet import alert
from skynet.common import CollectionError

TOKEN, USER = "a" * 30, "u" * 30
URL = "https://hc-ping.com/0f0e0d0c-aaaa-bbbb-cccc-123456789abc"


def _file(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "alerts.env"
    path.write_text(text)
    return path


def _good(tmp_path: Path, url: str = URL) -> Path:
    return _file(tmp_path, f"PUSHOVER_TOKEN={TOKEN}\nPUSHOVER_USER={USER}\nHEALTHCHECK_URL={url}\n")


@pytest.mark.parametrize("url", [
    "http://hc-ping.com/x", "https://user:pw@hc-ping.com/x", "https://hc-ping.com:8443/x",
    "https://hc-ping.com/x?y=1", "https://hc-ping.com",
])
def test_ping_url_must_be_plain_https(tmp_path: Path, url: str) -> None:
    with pytest.raises(alert.AlertError):
        alert.credentials(_good(tmp_path, url))


def test_missing_credentials_are_a_reason_not_an_exception(tmp_path: Path) -> None:
    assert alert.send("t", "m", path=tmp_path / "absent") == "alert credentials unavailable"
    assert alert.ping(path=tmp_path / "absent") == "alert credentials unavailable"


def test_send_posts_once_and_reports_transport_failure_safely(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[dict[str, Any]] = []

    def request(connection: Any, method: str, target: str, **kwargs: Any) -> Any:
        seen.append({"host": connection.host, "method": method, "target": target, **kwargs})
        return b"{}", None

    monkeypatch.setattr(alert.common, "request", request)
    assert alert.send("skynet: svc/demo", "DOWN", path=_good(tmp_path)) is None
    assert alert.ping(False, path=_good(tmp_path)) is None
    assert (seen[0]["host"], seen[0]["target"]) == ("api.pushover.net", "/1/messages.json")
    assert TOKEN.encode() in seen[0]["body"]
    assert (seen[1]["host"], seen[1]["target"]) == ("hc-ping.com", URL.split(".com")[1] + "/fail")

    def broken(*args: Any, **kwargs: Any) -> Any:
        raise CollectionError(f"leak {TOKEN}", 3)

    monkeypatch.setattr(alert.common, "request", broken)
    reason = alert.send("t", "m", path=_good(tmp_path))
    assert reason is not None and TOKEN not in reason and URL not in reason
