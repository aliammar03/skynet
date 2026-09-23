"""The disposable SQLite cache rebuilds from repository truth and never publishes a broken build."""

from pathlib import Path

import pytest

from skynet import cache


def test_rebuild_from_committed_inventory(repo_copy: Path) -> None:
    result = cache.build(repo_copy)
    assert result.guests > 0 and result.hosts > 0
    rows = cache.query(result.database, "SELECT COUNT(*) FROM guests").rows
    assert rows[0][0] == result.guests


def test_malformed_source_keeps_the_previous_database(repo_copy: Path) -> None:
    previous = cache.build(repo_copy).database.read_bytes()
    (repo_copy / "inventory/proxmox-core.json").write_text("{not json")
    with pytest.raises(cache.CacheError):
        cache.build(repo_copy)
    assert (repo_copy / ".cache/inventory.db").read_bytes() == previous


def test_query_without_database_is_unavailable(tmp_path: Path) -> None:
    with pytest.raises(cache.CacheError) as caught:
        cache.query(tmp_path / "missing.db", "SELECT 1")
    assert caught.value.code == 3
