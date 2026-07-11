from __future__ import annotations

from tests.support.ethos_cli_runner import run_ethos
from tests.support.lane_helpers import init_repo


def test_lane_resolution_inventory_exposes_empty_local_artifact_view(tmp_path) -> None:
    repo = init_repo(tmp_path / "repo")

    payload = run_ethos(
        "lane",
        "resolution",
        "inventory",
        "--root",
        repo.as_posix(),
        "--json",
        cwd=repo,
    )

    assert payload["ok"] is True
    assert payload["command"] == "lane resolution inventory"
    assert payload["state"] == "ready"
    assert payload["summary"] == {
        "package_count": 0,
        "receipt_count": 0,
        "clear_count": 0,
    }
    assert payload["data"]["entries"] == []
