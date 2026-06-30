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
    assert len(payload["data"]["pending_packages"]) == len(payload["required_gaps"])


def test_parity_gaps_exposes_concrete_backlog_packages() -> None:
    payload = run_ethos("parity", "gaps", "--json")

    package = payload["data"]["pending_packages"][0]
    assert package["gap"] == "parity_pending:work-lane-lifecycle"
    assert package["capability"] == "work-lane-lifecycle"
    assert package["target_home"] == "ethos-repository + ethos-adapters + ethos-test"
    assert package["required_tests"] == [
        "status/lane/prewrite golden JSON",
        "start lease and execution registry",
        "handoff and closeout dry-run/apply admission",
        "candidate lock and stale-base rejection",
        "foreign lane observe-only protection",
    ]
    assert package["parity_criterion"]
    assert package["rollback_impact"]


def test_parity_shadow_defaults_to_read_only_plan(tmp_path) -> None:
    payload = run_ethos("parity", "shadow", "--target", str(tmp_path), "--json")

    assert payload["ok"] is False
    assert payload["command"] == "parity shadow"
    assert payload["state"] == "planned"
    assert payload["data"]["comparisons"]
    assert payload["data"]["execution_packages"] == [
        {
            "gap": f"shadow_parity_not_executed:{tmp_path.resolve().as_posix()}",
            "state": "planned",
            "target": tmp_path.resolve().as_posix(),
            "commands": payload["data"]["comparisons"],
            "semantic_dimensions": payload["data"]["semantic_dimensions"],
            "blocking": True,
            "next_action": (
                f"ethos parity shadow --target {tmp_path.resolve().as_posix()} --execute"
            ),
        }
    ]


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
    assert {package["gap"] for package in payload["data"]["execution_packages"]} == set(
        payload["required_gaps"]
    )
