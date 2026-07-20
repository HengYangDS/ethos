from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from ethos.repository.adoption.planner import adoption_plan
from tests.support.ethos_cli_runner import run_ethos


def test_fleet_inspect_reports_external_adopter_shape(tmp_path: Path) -> None:
    adoption_plan(tmp_path, apply=True)

    payload = run_ethos("fleet", "inspect", "--target", str(tmp_path), "--json")

    assert payload["ok"] is True
    assert payload["command"] == "fleet inspect"
    assert payload["data"]["adopter"]["root"] == str(tmp_path.resolve())
    assert payload["data"]["adopter"]["binding"] == {
        "source": ".ethos/profile.toml",
        "ready": True,
    }
    assert payload["data"]["adopter"]["capabilities"]["openspec"] is False
    assert payload["data"]["adopter"]["capabilities"]["skills"] is False


def test_fleet_inspect_accepts_governed_docs_layout(tmp_path: Path) -> None:
    adoption_plan(tmp_path, apply=True)
    (tmp_path / "docs" / "governance").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "governance" / "README.md").write_text(
        "---\nsubject: docs:governance\nrole: reference\nstate: canonical\nrelations: test\n---\n"
        "# Governance Docs\n",
        encoding="utf-8",
    )

    payload = run_ethos("fleet", "inspect", "--target", str(tmp_path), "--json")

    assert payload["ok"] is True
    assert payload["data"]["adopter"]["capabilities"]["docs"] is True


def test_fleet_retirement_readiness_rejects_invalid_profile(tmp_path: Path) -> None:
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.parent.mkdir()
    profile.write_text("[", encoding="utf-8")

    payload = run_ethos("fleet", "retirement-readiness", "--target", str(tmp_path), "--json")

    assert payload["ok"] is False
    assert payload["required_gaps"] == ["adopter_profile_invalid:.ethos/profile.toml"]
