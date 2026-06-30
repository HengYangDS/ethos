from __future__ import annotations

from tests.support.ethos_cli_runner import run_ethos


def test_parity_ledger_has_no_unclassified_capabilities() -> None:
    payload = run_ethos("parity", "ledger", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "parity ledger"
    assert payload["summary"]["unclassified_count"] == 0
    assert {record["capability"] for record in payload["data"]["records"]} >= {
        "work-lane-lifecycle",
        "proof-evidence-chronicle",
        "campaign-hypothesis-evolution",
        "assistant-playbooks-skills",
        "quality-determinism-local-state",
        "openspec-claims-trust-review",
        "dmgr-domain-contract-profile",
    }


def test_parity_gaps_reports_alphasim_dmgr_shadow_gap() -> None:
    payload = run_ethos("parity", "gaps", "--adopter", "alphasim-dmgr", "--json")

    assert payload["ok"] is False
    assert payload["command"] == "parity gaps"
    assert "shadow_parity_pending:alphasim-dmgr" in payload["required_gaps"]


def test_parity_shadow_defaults_to_read_only_plan(tmp_path) -> None:
    payload = run_ethos("parity", "shadow", "--target", str(tmp_path), "--json")

    assert payload["ok"] is False
    assert payload["command"] == "parity shadow"
    assert payload["state"] == "planned"
    assert payload["data"]["comparisons"]


def test_parity_shadow_execute_reports_missing_embedded_backend(tmp_path) -> None:
    payload = run_ethos(
        "parity",
        "shadow",
        "--target",
        str(tmp_path),
        "--execute",
        "--timeout-seconds",
        "5",
        "--json",
    )

    assert payload["ok"] is False
    assert payload["state"] == "different"
    assert any(gap.startswith("embedded_command_failed:") for gap in payload["required_gaps"])
