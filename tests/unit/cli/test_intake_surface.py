from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from tests.support.ethos_cli_runner import run_ethos


def test_intake_status_is_public_read_only_surface() -> None:
    payload = run_ethos("intake", "status", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "intake status"
    assert payload["data"]["truth_boundary"] == "adopter-ledger"
    assert payload["data"]["projection"]["truth_boundary"] == "projection-evidence"
    assert payload["data"]["projection"]["repository_truth"] is False
    assert payload["data"]["provider"] == "unconfigured"


def test_intake_status_rejects_empty_configuration(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / ".ethos").mkdir(parents=True)
    (root / ".ethos" / "intake.toml").write_text("", encoding="utf-8")

    payload = run_ethos("intake", "status", "--root", str(root), "--json")

    assert payload["ok"] is False
    assert payload["state"] == "invalid"
    assert payload["data"]["configured"] is False
    assert payload["data"]["provider"] == "invalid"
    assert "intake_provider_missing:.ethos/intake.toml" in payload["required_gaps"]
