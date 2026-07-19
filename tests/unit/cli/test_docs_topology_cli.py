from __future__ import annotations

from tests.support.ethos_cli_runner import run_ethos


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
