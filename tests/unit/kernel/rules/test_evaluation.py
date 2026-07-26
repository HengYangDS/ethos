from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from ethos.contracts.rules import RuleEvalRequest
from ethos.contracts.rules import RuleFactSnapshot
from ethos.repository.policy.rules.check import rules_layer_report
from ethos.repository.policy.rules.evaluation import active_valid_exceptions
from ethos.repository.policy.rules.evaluation import fact_gaps
from ethos.repository.policy.rules.evaluation import match_waiver
from ethos.repository.policy.rules.evaluation import required_gate_details
from ethos.repository.policy.rules.evaluation import rules_evaluation_report
from ethos.repository.policy.rules.evaluation import scope_matches_path
from ethos.repository.policy.rules.exceptions import rules_docs_manifest_report
from ethos.repository.policy.schema import validate_schema_instance
from tests.unit.kernel.rules.snapshots import complete_snapshot
from tests.unit.kernel.rules.snapshots import fact


def test_rule_evaluation_blocks_missing_authorization_for_publish(
    tmp_path: Path,
) -> None:
    report = rules_evaluation_report(
        tmp_path,
        phase="publish",
        changed_paths=(),
        mutation=True,
        authorized=False,
    )

    assert report["state"] == "block"
    assert "authorization_required" in report["required_gaps"]
    assert report["decisions"][0]["decision"] == "block"


def test_rule_evaluation_uses_authorization_fact_over_arguments(tmp_path: Path) -> None:
    snapshot = complete_snapshot(phase="publish", mutation=True, authorized=False)

    report = rules_evaluation_report(
        tmp_path,
        phase="publish",
        mutation=True,
        authorized=True,
        fact_snapshot=snapshot,
    )

    assert report["state"] == "block"
    assert "authorization_required" in report["required_gaps"]


def test_rule_evaluation_uses_fact_snapshot_and_fail_closed_inputs(
    tmp_path: Path,
) -> None:
    missing_fact = RuleFactSnapshot(
        phase="plan",
        head="untracked",
        facts={
            "changed_paths": fact([], owner="ethos-adapters", available=False),
        },
    )

    report = rules_evaluation_report(
        tmp_path,
        phase="plan",
        fact_snapshot=missing_fact,
    )

    assert report["state"] == "block"
    assert report["fact_snapshot_digest"] == missing_fact.digest
    assert "fact_unavailable:changed_paths" in report["required_gaps"]
    assert report["source_refs"]


def test_rule_evaluation_blocks_incomplete_fact_snapshot(tmp_path: Path) -> None:
    snapshot = RuleFactSnapshot(phase="plan", head="untracked", facts={})

    report = rules_evaluation_report(tmp_path, phase="plan", fact_snapshot=snapshot)

    assert report["state"] == "block"
    assert "fact_missing:changed_paths" in report["required_gaps"]
    assert "fact_missing:prewrite" in report["required_gaps"]


def test_rule_eval_request_snapshot_requires_prewrite_source_fact(
    tmp_path: Path,
) -> None:
    snapshot = RuleEvalRequest(
        phase="publish",
        changed_paths=("README.md",),
        mutation=True,
        authorized=True,
    ).to_fact_snapshot(head="abc123")

    report = rules_evaluation_report(tmp_path, phase="publish", fact_snapshot=snapshot)

    assert "prewrite" in snapshot.facts
    assert "fact_unavailable:prewrite" in report["required_gaps"]


def test_rule_evaluation_matches_trailing_directory_glob(tmp_path: Path) -> None:
    report = rules_evaluation_report(
        tmp_path,
        phase="plan",
        changed_paths=("docs",),
        fact_snapshot=complete_snapshot(changed_paths=("docs",)),
    )

    assert report["state"] == "advisory"
    assert report["required_gates"] == ["docs-registry"]
    assert any(match["rule_id"] == "starter.docs" for match in report["surface_matches"])


def test_rule_evaluation_helper_edges(tmp_path: Path) -> None:
    gaps = fact_gaps(
        RuleFactSnapshot(
            phase="plan",
            head="untracked",
            facts={
                "malformed": "not-a-dict",
                "noowner": {"available": True, "value": {}},
            },
        )
    )
    assert {"fact_malformed:malformed", "fact_owner_missing:noowner"} <= set(gaps)
    assert scope_matches_path("branch:feature", "src/a.py") is False
    assert (
        active_valid_exceptions({"required_gaps": [], "exceptions": [{"status": "expired"}]}) == []
    )
    assert (
        match_waiver(rule_id="wanted", path="notes/todo.md", exceptions=[{"rule_id": "other"}])
        is None
    )
    assert (
        match_waiver(
            rule_id="r",
            path="src/a.py",
            exceptions=[{"rule_id": "r", "scope": "path:other"}],
        )
        is None
    )
    invalid = RuleEvalRequest(phase="nonsense").to_fact_snapshot(head="untracked")
    assert (
        "invalid_rule_phase:nonsense"
        in rules_evaluation_report(tmp_path, phase="nonsense", fact_snapshot=invalid)[
            "required_gaps"
        ]
    )
    prove = rules_evaluation_report(tmp_path, phase="prove", changed_paths=(".ethos/rules.toml",))
    assert not any(gap.startswith("gate_required:") for gap in prove["required_gaps"])
    assert required_gate_details([{"required_gates_detail": [{"command": "x"}]}]) == []


def test_rule_evaluation_blocks_timeout_nondeterminism_and_conflicts(
    tmp_path: Path,
) -> None:
    snapshot = complete_snapshot()
    snapshot.facts.update(
        {
            "adapter": fact(
                {"timeout": True}, owner="ethos-adapters", fresh=False, available=False
            ),
            "compiler": fact({"deterministic": False}, owner="ethos-repository"),
            "merge": fact({"unresolved_conflicts": ["rules/a.toml"]}, owner="ethos-repository"),
        }
    )

    report = rules_evaluation_report(tmp_path, phase="plan", fact_snapshot=snapshot)

    assert report["state"] == "block"
    assert "fact_unavailable:adapter" in report["required_gaps"]
    assert "fact_stale:adapter" in report["required_gaps"]
    assert "fact_timeout:adapter" in report["required_gaps"]
    assert "fact_nondeterministic:compiler" in report["required_gaps"]
    assert "fact_unresolved_conflicts:merge" in report["required_gaps"]


def test_rule_evaluation_ignores_non_authoritative_claim_and_interface_facts(
    tmp_path: Path,
) -> None:
    snapshot = complete_snapshot(phase="prove")
    snapshot.facts.update(
        {
            "claim_state": fact(
                {"ok": False, "required_gaps": ["claim_digest_mismatch:rules"]},
                owner="ethos-repository.claims",
            ),
            "evidence_freshness": fact(
                {"ok": False, "stale": ["evidence/rules.md"]},
                owner="ethos-repository.claims",
            ),
            "interface_projection": fact(
                {"ok": False, "required_gaps": ["parallel_interface_truth"]},
                owner="ethos-interface-projection",
            ),
        }
    )

    report = rules_evaluation_report(tmp_path, phase="prove", fact_snapshot=snapshot)

    assert not any(
        name in gap
        for gap in report["required_gaps"]
        for name in ("claim_state", "evidence_freshness", "interface_projection")
    )


def test_rule_evaluation_blocks_worktree_gaps_for_publish(tmp_path: Path) -> None:
    snapshot = complete_snapshot(phase="publish")
    snapshot.facts["worktree"]["value"] = {
        "ok": False,
        "required_gaps": ["protected_root_mutation"],
    }

    report = rules_evaluation_report(tmp_path, phase="publish", fact_snapshot=snapshot)

    assert report["state"] == "block"
    assert "fact_required_gap:worktree:protected_root_mutation" in report["required_gaps"]


def test_inactive_profile_rule_does_not_affect_generic_evaluation(
    tmp_path: Path,
) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "rules.toml").write_text(
        """
[profiles]
active = ["generic"]

[[rule]]
id = "strict.docs"
owner = "docs-team"
profile_layers = ["strict"]
authority_ref = "docs/governance/docs.md"
contract_ref = "docs/governance/docs.md"
path_globs = ["notes/**"]
severity = "blocking"
required_gates = ["docs-registry"]
stop_condition = "strict_docs_gap"
""".lstrip(),
        encoding="utf-8",
    )

    report = rules_evaluation_report(
        tmp_path,
        phase="plan",
        changed_paths=("notes/todo.md",),
        fact_snapshot=complete_snapshot(changed_paths=("notes/todo.md",)),
    )

    assert "strict.docs" not in report["effective_rules"]
    assert "rules_uncovered_path:notes/todo.md" in report["required_gaps"]
    assert not any("strict.docs" in gap for gap in report["required_gaps"])


def test_blocking_rule_required_gate_is_enforced(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "rules.toml").write_text(
        """
[profiles]
active = ["generic"]

[[rule]]
id = "custom.docs"
owner = "docs-team"
authority_ref = "docs/governance/docs.md"
contract_ref = "docs/governance/docs.md"
path_globs = ["notes/**"]
severity = "blocking"
required_gates = ["docs-registry"]
stop_condition = "docs_gap"
""".lstrip(),
        encoding="utf-8",
    )

    report = rules_evaluation_report(
        tmp_path,
        phase="plan",
        changed_paths=("notes/todo.md",),
        fact_snapshot=complete_snapshot(changed_paths=("notes/todo.md",)),
    )

    assert report["state"] == "block"
    assert "gate_required:custom.docs:docs-registry" in report["required_gaps"]
    assert {
        "id": "docs-registry",
        "kind": "require_gate",
        "scope": "repository",
        "actor": "local",
        "blocking": True,
    } in report["obligations"]
    assert validate_schema_instance("rule-evaluation.schema.json", report)["ok"]


def test_rule_layer_does_not_hide_depth_or_exception_gaps(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "rules.toml").write_text(
        """
[profiles]
active = ["strict"]
""".lstrip(),
        encoding="utf-8",
    )

    report = rules_layer_report(tmp_path)

    assert report["ok"] is False
    assert report["depth_ok"] is False
    assert set(report["depth_tiers"]) == {
        "subject",
        "contract",
        "transition",
        "evidence",
        "stop",
    }
    assert report["depth_tiers"]["subject"] is True
    assert report["depth_tiers"]["contract"] is False
    assert "rules_strict_subject_coverage_missing" in report["required_gaps"]


def test_rules_docs_manifest_reports_missing_rule_doc_refs(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "rules.toml").write_text(
        """
[profiles]
active = ["generic"]

[[rule]]
id = "custom.docs"
owner = "docs-team"
authority_ref = "docs/missing-authority.md"
contract_ref = "docs/missing-contract.md"
path_globs = ["docs/**"]
severity = "advisory"
required_gates = []
stop_condition = "docs_missing"
""".lstrip(),
        encoding="utf-8",
    )

    report = rules_docs_manifest_report(tmp_path)
    layer = rules_layer_report(tmp_path)

    assert report["ok"] is False
    assert report["generated_from"] == "compiled-rules"
    assert "missing_doc_ref:docs/missing-authority.md" in report["required_gaps"]
    assert layer["docs_manifest_ok"] is False
    assert "rules_docs_manifest:missing_doc_ref:docs/missing-contract.md" in layer["required_gaps"]
