from __future__ import annotations

from tests.support.ethos_cli_runner import run_ethos


def test_explain_projects_gap_to_invalid_state_taxonomy() -> None:
    payload = run_ethos("explain", "parity_evidence_invalid:generic:product_head", "--json")

    assert payload["ok"] is True
    assert payload["state"] == "explained"
    assert payload["summary"] == {
        "gap": "parity_evidence_invalid:generic:product_head",
        "invalid_state": "evidence_missing_or_stale",
    }
    assert payload["data"]["invalid_state"] == {
        "id": "evidence_missing_or_stale",
        "node": "Evidence",
        "question": "Is the evidence present, fresh, HEAD-bound, and actually executed?",
        "summary": (
            "The Evidence — executed proof, gate result, digest, or freshness "
            "binding — is missing, stale, dry-run-only, or not bound to the "
            "pushed/expected HEAD."
        ),
    }
    assert payload["data"]["taxonomy"]["projection_only"] is True
    assert payload["data"]["taxonomy"]["lifecycle_command"] is False


def test_report_classifies_current_gap_layers_into_invalid_states() -> None:
    payload = run_ethos("report", "--json")

    parity_gaps = payload["data"]["gap_layers"]["capability_parity"]["required_gaps"]
    invalid_states = payload["data"]["gap_layers"]["capability_parity"]["invalid_states"]
    assert invalid_states["gap_count"] == len(parity_gaps)
    if parity_gaps:
        assert set(invalid_states["categories"]).issubset(
            {
                "evidence_missing_or_stale",
                "carrier_invalid",
                "change_unbounded",
                "substrate_untrusted",
            }
        )
        assert payload["data"]["invalid_states"]["gap_count"] >= len(parity_gaps)


def test_explain_projects_advisory_signal_without_required_gap_overclaim() -> None:
    signal = (
        "openspec_protected_branch_active_change_unarchived:"
        "main:release_root:ethos-release-hardening"
    )
    payload = run_ethos("explain", signal, "--json")

    assert payload["ok"] is True
    assert payload["state"] == "explained"
    assert payload["summary"] == {"gap": signal, "invalid_state": "carrier_invalid"}
    assert payload["data"]["signal"] == signal
    assert payload["data"]["kind"] == "invalid_state_projection"
    assert "required gap" not in payload["data"]["meaning"]
    assert "signal" in payload["data"]["meaning"]
    assert payload["data"]["taxonomy"]["projection_only"] is True
