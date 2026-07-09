from __future__ import annotations

from pathlib import Path

from ethos.repository.adoption.planner import adoption_plan
from tests.support.ethos_cli_runner import run_ethos


def test_fleet_inspect_reports_external_adopter_shape(tmp_path: Path) -> None:
    (tmp_path / ".gitlab").mkdir()
    adoption_plan(tmp_path, profile="gitlab", apply=True)

    payload = run_ethos("fleet", "inspect", "--target", str(tmp_path), "--json")

    assert payload["ok"] is True
    assert payload["command"] == "fleet inspect"
    assert payload["data"]["adopter"]["root"] == str(tmp_path.resolve())
    assert payload["data"]["adopter"]["governance"]["ethos_config"] is True
    assert payload["data"]["adopter"]["governance"]["openspec"] is True
    assert payload["data"]["adopter"]["governance"]["skills"] is True


def test_fleet_inspect_accepts_governed_docs_layout(tmp_path: Path) -> None:
    adoption_plan(tmp_path, profile="generic", apply=True)
    (tmp_path / "docs" / "index.md").unlink()
    (tmp_path / "docs" / "governance").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "governance" / "README.md").write_text(
        "---\nsubject: docs:governance\nrole: reference\nstate: canonical\nrelations: test\n---\n"
        "# Governance Docs\n",
        encoding="utf-8",
    )

    payload = run_ethos("fleet", "inspect", "--target", str(tmp_path), "--json")

    assert payload["ok"] is True
    assert payload["data"]["adopter"]["governance"]["docs"] is True
