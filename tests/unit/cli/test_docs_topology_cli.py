from __future__ import annotations

from typing import TYPE_CHECKING

from tests.support.ethos_cli_runner import run_ethos

if TYPE_CHECKING:
    from pathlib import Path


def test_quality_docs_topology_command_reports_common_kernel() -> None:
    payload = run_ethos("quality", "docs-topology", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "quality docs-topology"
    assert payload["state"] == "clean"
    assert payload["required_gaps"] == []
    required = {item["path"] for item in payload["data"]["required_paths"]}
    assert "docs/README.md" in required
    assert "docs/decisions/templates/decision-record.md" in required
    assert "docs/index.md" not in required
    assert "docs/start/quickstart.md" not in required
    assert "docs/governance/README.md" not in required
    assert "docs/plans/README.md" not in required
    assert payload["data"]["contract"]["adopter_neutral"] is True
    assert (
        payload["data"]["contract"]["principle"]
        == "minimal semantic documentation kernel across governed repositories"
    )


def _write_required_docs(root: Path) -> None:
    required = [
        "docs/README.md",
        "docs/decisions/README.md",
        "docs/decisions/decision-index.md",
        "docs/decisions/decision-dependency-map.md",
        "docs/decisions/decision-code-links.md",
        "docs/decisions/accepted/README.md",
        "docs/decisions/superseded/README.md",
        "docs/decisions/templates/README.md",
        "docs/decisions/templates/decision-record.md",
        "docs/evidence/README.md",
        "docs/history/README.md",
        "docs/reference/README.md",
    ]
    for relative in required:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("---\nstate: canonical\n---\n# doc\n", encoding="utf-8")


def test_quality_docs_topology_cli_reports_adopter_declared_compatibility_policy(
    tmp_path: Path,
) -> None:
    _write_required_docs(tmp_path)
    profile = tmp_path / ".ethos/profile.toml"
    profile.parent.mkdir(parents=True)
    profile.write_text(
        'schema_version = 1\nprofile_id = "sample-adopter"\nprofile_version = "1"\nethos_contract_version = "1"\n\n[roots]\ndocs = "docs"\n\n[docs_topology]\nstate_root_policy = "adopter_declared_compatibility"\ntime_state_roots = ["docs/current", "docs/future"]\ncompatibility_decision = "docs/reference/documentation-information-architecture.md"\n',
        encoding="utf-8",
    )
    (tmp_path / "docs/current").mkdir(parents=True)
    (tmp_path / "docs/future").mkdir(parents=True)
    (tmp_path / "docs/reference/documentation-information-architecture.md").write_text(
        "---\nstate: canonical\nrole: reference\n---\n# IA\n",
        encoding="utf-8",
    )

    payload = run_ethos("quality", "docs-topology", "--root", tmp_path.as_posix(), "--json")

    assert payload["ok"] is True
    assert payload["required_gaps"] == []
    assert payload["data"]["time_state_roots"] == ["docs/current", "docs/future"]
    assert (
        payload["data"]["profile_policy"]["state_root_policy"] == "adopter_declared_compatibility"
    )
