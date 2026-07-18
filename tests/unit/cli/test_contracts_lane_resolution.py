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


def test_lane_resolution_clear_exposes_bounded_refusal_contract(tmp_path) -> None:
    repo = init_repo(tmp_path / "repo")

    payload = run_ethos(
        "lane",
        "resolution",
        "clear",
        "--decision-id",
        "lane-decision:missing",
        "--expect-manifest-sha256",
        "a" * 64,
        "--chronicle-ref",
        "evidence/chronicle/missing.md",
        "--reason",
        "A retained package must be selected exactly.",
        "--break-glass",
        "--confirm-irreversible",
        "--json",
        cwd=repo,
    )

    assert payload["ok"] is False
    assert payload["command"] == "lane resolution clear"
    assert "lane_resolution_clear_package_missing" in payload["required_gaps"]
