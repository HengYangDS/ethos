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
        "reference-adopter-domain-contract-profile",
    }
