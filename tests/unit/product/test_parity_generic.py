from __future__ import annotations

import hashlib
import subprocess
from typing import TYPE_CHECKING

import pytest

from ethos.adapters import shadow
from ethos.adapters.shadow import _accepted_semantic_differences
from ethos.adapters.shadow import _semantic_diff
from ethos.adapters.shadow import run_shadow_parity
from ethos.domain.land import acceptable_parity_product_heads
from ethos.repository.evidence.parity import _command_matches_identity
from ethos.repository.evidence.parity import _parity_evidence
from ethos.repository.evidence.parity import _validate_parity_evidence
from ethos.repository.policy.schema import validate_schema_instance

if TYPE_CHECKING:
    from pathlib import Path

MIGRATED_CAPABILITIES = [
    "work-lane-lifecycle",
    "proof-evidence-chronicle",
    "campaign-hypothesis-evolution",
    "assistant-playbooks-skills",
    "quality-determinism-local-state",
    "openspec-claims-trust-review",
]

SHADOW_COMMANDS = [
    "ethos status --json",
    "ethos plan --changed --json",
    "ethos prove --json",
    "ethos report --json",
    "ethos quality command-surface --json",
    "ethos assistants doctor --json",
    "ethos playbooks route --changed --json",
    "ethos land --json",
    "ethos publish --json",
]


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _init_git_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "dev"], cwd=path, check=True, capture_output=True)
    (path / "README.md").write_text("# sample\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test User",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            "init",
        ],
        cwd=path,
        check=True,
        capture_output=True,
    )
    return path


def _git_head(path: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=path,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


def _complete_parity_evidence(adopter: str) -> dict[str, object]:
    command = (
        f"uv run --package ethos ethos parity shadow --adopter {adopter} "
        f"--target /tmp/{adopter} --execute --timeout-seconds 30 --json"
    )
    return {
        "schema_version": 1,
        "adopter": adopter,
        "target": f"/tmp/{adopter}",
        "generated_on": "2026-07-01",
        "command": command,
        "freshness": {
            "product_head": "product-head",
            "target_head": "target-head",
            "command_sha256": _sha256_text(command),
        },
        "shadow": {
            "ok": True,
            "required_gaps": [],
            "comparison_count": len(SHADOW_COMMANDS),
            "commands": SHADOW_COMMANDS,
        },
        "verified_capabilities": MIGRATED_CAPABILITIES,
        "capability_basis": {
            capability: [f"{capability} shadow parity basis"]
            for capability in MIGRATED_CAPABILITIES
        },
    }


def _retarget_parity_evidence(
    evidence: dict[str, object],
    *,
    adopter: str,
    target: Path,
    timeout_seconds: int = 30,
) -> None:
    command = (
        f"uv run --package ethos ethos parity shadow --adopter {adopter} "
        f"--target {target.resolve().as_posix()} --execute "
        f"--timeout-seconds {timeout_seconds} --json"
    )
    evidence["target"] = target.resolve().as_posix()
    evidence["command"] = command
    freshness = evidence["freshness"]
    assert isinstance(freshness, dict)
    freshness["command_sha256"] = _sha256_text(command)


def test_shadow_semantic_diff_compares_plan_gate_dimension() -> None:
    external = {
        "ok": True,
        "command": "plan",
        "state": "planned",
        "summary": {"required_gate_count": 1},
        "data": {"required_gates": [{"id": "unit"}]},
    }
    embedded = {
        "ok": True,
        "command": "plan",
        "state": "planned",
        "summary": {"required_gate_count": 0},
        "data": {"required_gates": []},
    }

    diff = shadow._semantic_diff(("plan", "--changed"), external, embedded)

    assert diff == {"required_gate_ids": {"external": ["unit"], "embedded": []}}


def test_shadow_status_projection_accepts_embedded_top_level_fields() -> None:
    external = {
        "ok": True,
        "command": "status",
        "state": "ready",
        "required_gaps": [],
        "data": {"role": "accepted_root", "dirty": False, "changed_paths": []},
    }
    embedded = {
        "ok": True,
        "command": "status",
        "required_gaps": [],
        "role": "accepted_root",
        "dirty": False,
        "changed_paths": [],
    }

    assert shadow._semantic_diff(("status",), external, embedded) == {}


def test_shadow_report_projection_normalizes_missing_blocking_gap_count() -> None:
    external = {"ok": True, "command": "report", "state": "ready", "required_gaps": []}
    embedded = {
        "ok": True,
        "command": "report",
        "summary": {"blocking_gap_count": 0},
        "required_gaps": [],
        "scorecards": [{"id": "governance", "ok": True, "required_gaps": []}],
    }

    assert shadow._semantic_diff(("report",), external, embedded) == {}


def test_shadow_playbooks_projection_ignores_schema_specific_route_details() -> None:
    external = {
        "ok": True,
        "command": "playbooks route",
        "state": "routed",
        "required_gaps": [],
        "data": {"selected": [{"id": "repo-local-skill"}]},
    }
    embedded = {
        "ok": True,
        "command": "playbooks route",
        "required_gaps": [],
        "route_hints": [],
    }

    assert shadow._semantic_diff(("playbooks", "route", "--changed"), external, embedded) == {}


def test_shadow_parse_failure_is_process_failure() -> None:
    result = {
        "exit_code": 0,
        "stdout": "not json",
        "stderr": "",
        "json": {},
    }

    assert shadow._process_failed(result) is True


def test_shadow_timeout_is_process_failure() -> None:
    result = {
        "exit_code": 124,
        "stdout": "",
        "stderr": "timeout",
        "json": {},
    }

    assert shadow._process_failed(result) is True


def test_shadow_semantic_diff_derives_state_for_minimal_status_payload() -> None:
    external = {
        "ok": True,
        "command": "status",
        "state": "ready",
        "required_gaps": [],
        "data": {"role": "accepted_root"},
    }
    embedded = {
        "ok": True,
        "command": "status",
        "summary": {"dirty": False},
        "required_gaps": [],
        "role": "accepted_root",
    }

    assert _semantic_diff(external, embedded) == {}


def test_shadow_semantic_diff_derives_state_for_legacy_plan_payload() -> None:
    external = {
        "ok": True,
        "command": "plan",
        "state": "planned",
        "required_gaps": [],
    }
    embedded = {
        "ok": True,
        "command": "plan",
        "summary": {"changed_path_count": 0},
        "required_gaps": [],
    }

    assert _semantic_diff(external, embedded) == {}


def test_shadow_semantic_diff_derives_state_for_legacy_assistants_doctor_payload() -> None:
    external = {
        "ok": True,
        "command": "assistants doctor",
        "state": "ready",
        "required_gaps": [],
    }
    embedded = {
        "ok": True,
        "command": "assistants doctor",
        "summary": {"surface_count": 4},
        "required_gaps": [],
    }

    assert _semantic_diff(external, embedded) == {}


def test_shadow_semantic_diff_normalizes_ready_prove_against_minimal_payload() -> None:
    external = {
        "ok": True,
        "command": "prove",
        "state": "ready",
        "required_gaps": [],
    }
    embedded = {
        "ok": True,
        "command": "prove",
        "state": {},
        "required_gaps": [],
    }

    assert _semantic_diff(("prove",), external, embedded) == {}


@pytest.mark.parametrize(
    ("command", "external_state"),
    [
        ("prove", "gapped"),
        ("report", "gapped"),
        ("land", "dry_run"),
        ("publish", "dry_run"),
    ],
)
def test_shadow_semantic_diff_classifies_external_repository_audit_gaps_for_minimal_payload(
    command: str,
    external_state: str,
) -> None:
    external = {
        "ok": False,
        "command": command,
        "state": external_state,
        "required_gaps": [
            "docs/architecture/product-ontology.md",
            "claims_missing",
        ],
        "data": {
            "repository_audit": {
                "required_gaps": [
                    "docs/architecture/product-ontology.md",
                    "claims_missing",
                ],
            },
        },
    }
    embedded = {
        "ok": True,
        "command": command,
        "summary": {"command": command, "role": "accepted_root"},
        "required_gaps": [],
    }

    assert _semantic_diff(external, embedded) == {}


def test_shadow_semantic_diff_preserves_external_non_repository_audit_gaps() -> None:
    external = {
        "ok": False,
        "command": "prove",
        "state": "gapped",
        "required_gaps": [
            "docs/architecture/product-ontology.md",
            "action_graph_invalid",
        ],
        "data": {
            "repository_audit": {
                "required_gaps": ["docs/architecture/product-ontology.md"],
            },
        },
    }
    embedded = {
        "ok": True,
        "command": "prove",
        "summary": {"command": "prove"},
        "required_gaps": [],
    }

    diff = _semantic_diff(external, embedded)

    assert diff["ok"] == {"external": False, "embedded": True}
    assert diff["required_gaps"] == {"external": ["action_graph_invalid"], "embedded": []}


def test_shadow_semantic_diff_classifies_changed_route_noop() -> None:
    external = {
        "ok": False,
        "command": "playbooks route",
        "state": "gapped",
        "required_gaps": [
            "skill_missing_id",
            "skill_missing_id",
            "playbook_route_missing:changed-scope",
        ],
        "data": {
            "subject": "changed-scope",
            "required_gaps": [
                "skill_missing_id",
                "skill_missing_id",
                "playbook_route_missing:changed-scope",
            ],
        },
    }
    embedded = {
        "ok": True,
        "command": "playbooks route",
        "summary": {
            "changed_requested": True,
            "changed_path_count": 0,
            "command": "playbooks route",
        },
        "required_gaps": [],
    }

    assert _semantic_diff(external, embedded) == {}


def test_shadow_semantic_diff_classifies_changed_route_noop_with_strict_activation_gap() -> None:
    external = {
        "ok": False,
        "command": "playbooks route",
        "state": "gapped",
        "required_gaps": [
            "skill_missing_id",
            "playbook_activation_unsupported_version:1",
        ],
        "data": {
            "subject": "changed-scope",
            "required_gaps": [
                "skill_missing_id",
                "playbook_activation_unsupported_version:1",
            ],
        },
    }
    embedded = {
        "ok": True,
        "command": "playbooks route",
        "summary": {
            "changed_requested": True,
            "changed_path_count": 0,
            "command": "playbooks route",
        },
        "required_gaps": [],
    }

    assert _semantic_diff(external, embedded) == {}
    assert _accepted_semantic_differences(external, embedded) == [
        {
            "kind": "changed_route_noop",
            "classification": "accepted",
            "scope": "changed_scope_route",
            "commands": ["ethos playbooks route"],
            "gaps": [
                "playbook_activation_unsupported_version:1",
                "skill_missing_id",
            ],
            "reason": "changed-scope route has no changed paths to route",
        }
    ]


def test_shadow_semantic_diff_classifies_report_parity_evidence_refresh_bootstrap() -> None:
    external = {
        "ok": False,
        "command": "report",
        "state": "gapped",
        "summary": {
            "score": 6,
            "max_score": 7,
            "governance_gap_count": 0,
            "parity_pending_count": 6,
        },
        "required_gaps": [],
    }
    embedded = {
        "ok": True,
        "command": "report",
        "state": "ready",
        "summary": {"blocking_gap_count": 0},
        "required_gaps": [],
    }

    assert _semantic_diff(external, embedded) == {}
    accepted = _accepted_semantic_differences(external, embedded)
    assert accepted == [
        {
            "kind": "report_parity_evidence_refresh_bootstrap",
            "classification": "accepted",
            "scope": "parity_evidence_refresh",
            "commands": ["ethos report"],
            "gaps": ["parity_pending_count:6"],
            "reason": "report parity freshness is being refreshed by the current shadow run",
        }
    ]

    payload = {
        "ok": True,
        "state": "matched",
        "target": "/repo",
        "required_gaps": [],
        "accepted_summary": {
            "total_count": 1,
            "command_count": 1,
            "kind_counts": {"report_parity_evidence_refresh_bootstrap": 1},
        },
        "comparisons": [
            {
                "command": "ethos report",
                "external": {"exit_code": 0, "stdout": "", "stderr": "", "json": external},
                "embedded": {"exit_code": 0, "stdout": "", "stderr": "", "json": embedded},
                "semantic_diff": {},
                "accepted_summary": {
                    "total_count": 1,
                    "kind_counts": {"report_parity_evidence_refresh_bootstrap": 1},
                },
                "accepted_differences": accepted,
            }
        ],
        "execution_packages": [],
    }

    validation = validate_schema_instance("shadow-parity.schema.json", payload)
    assert validation["ok"] is True


def test_shadow_semantic_diff_preserves_changed_route_gap_when_paths_changed() -> None:
    external = {
        "ok": False,
        "command": "playbooks route",
        "state": "gapped",
        "required_gaps": ["playbook_route_missing:changed-scope"],
        "data": {"subject": "changed-scope"},
    }
    embedded = {
        "ok": True,
        "command": "playbooks route",
        "summary": {
            "changed_requested": True,
            "changed_path_count": 1,
            "command": "playbooks route",
        },
        "required_gaps": [],
    }

    diff = _semantic_diff(external, embedded)

    assert diff["required_gaps"] == {
        "external": ["playbook_route_missing:changed-scope"],
        "embedded": [],
    }


def test_shadow_accepted_difference_exposes_counts_and_command_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_external(
        target: Path,
        command: tuple[str, ...],
        *,
        timeout_seconds: int,
    ) -> dict[str, object]:
        _ = (target, timeout_seconds)
        command_name = command[0] if command[0] != "assistants" else "assistants doctor"
        if command[:2] == ("quality", "command-surface"):
            command_name = "quality command-surface"
        if command[0] == "playbooks":
            command_name = "playbooks route"
        if command == ("prove",):
            payload = {
                "ok": False,
                "command": "prove",
                "state": "gapped",
                "required_gaps": ["claims_missing"],
                "data": {"repository_audit": {"required_gaps": ["claims_missing"]}},
            }
        else:
            state_by_command = {
                "status": "ready",
                "plan": "planned",
                "report": "ready",
                "quality command-surface": "clean",
                "assistants doctor": "ready",
                "playbooks route": "routed",
                "land": "ready_to_land",
                "publish": "ready_to_publish",
            }
            payload = {
                "ok": True,
                "command": command_name,
                "state": state_by_command[command_name],
                "required_gaps": [],
            }
        return {"exit_code": 0, "stdout": "", "stderr": "", "json": payload}

    def fake_embedded(
        target: Path,
        command: tuple[str, ...],
        *,
        timeout_seconds: int,
    ) -> dict[str, object]:
        _ = (target, timeout_seconds)
        command_name = command[0] if command[0] != "assistants" else "assistants doctor"
        if command[:2] == ("quality", "command-surface"):
            command_name = "quality command-surface"
        if command[0] == "playbooks":
            command_name = "playbooks route"
        state_by_command = {
            "status": "ready",
            "plan": "planned",
            "prove": "proven",
            "report": "ready",
            "quality command-surface": "clean",
            "assistants doctor": "ready",
            "playbooks route": "routed",
            "land": "ready_to_land",
            "publish": "ready_to_publish",
        }
        return {
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "json": {
                "ok": True,
                "command": command_name,
                "state": state_by_command[command_name],
                "required_gaps": [],
            },
        }

    monkeypatch.setattr("ethos.adapters.shadow._run_external", fake_external)
    monkeypatch.setattr("ethos.adapters.shadow._run_embedded", fake_embedded)

    payload = run_shadow_parity(tmp_path, timeout_seconds=5)

    assert payload["ok"] is True
    assert payload["accepted_summary"] == {
        "total_count": 1,
        "command_count": 1,
        "kind_counts": {"external_product_repository_audit_gap": 1},
    }
    comparison = next(item for item in payload["comparisons"] if item["command"] == "ethos prove")
    assert comparison["accepted_summary"] == {
        "total_count": 1,
        "kind_counts": {"external_product_repository_audit_gap": 1},
    }
    assert comparison["accepted_differences"] == [
        {
            "kind": "external_product_repository_audit_gap",
            "classification": "accepted",
            "scope": "external_product_repository_audit",
            "commands": ["ethos prove"],
            "gaps": ["claims_missing"],
            "reason": "external product repository audit gap is not an embedded adopter parity gap",
        }
    ]

    validation = validate_schema_instance("shadow-parity.schema.json", payload)
    assert validation["ok"] is True


def test_shadow_accepted_difference_schema_rejects_unknown_kind() -> None:
    payload = {
        "ok": True,
        "state": "matched",
        "target": "/repo",
        "required_gaps": [],
        "accepted_summary": {
            "total_count": 1,
            "command_count": 1,
            "kind_counts": {"unknown": 1},
        },
        "comparisons": [
            {
                "command": "ethos prove",
                "external": {"exit_code": 0, "stdout": "", "stderr": "", "json": {}},
                "embedded": {"exit_code": 0, "stdout": "", "stderr": "", "json": {}},
                "semantic_diff": {},
                "accepted_summary": {"total_count": 1, "kind_counts": {"unknown": 1}},
                "accepted_differences": [
                    {
                        "kind": "unknown",
                        "classification": "accepted",
                        "scope": "external_product_repository_audit",
                        "commands": ["ethos prove"],
                        "gaps": ["claims_missing"],
                        "reason": "invalid",
                    }
                ],
            }
        ],
        "execution_packages": [],
    }

    validation = validate_schema_instance("shadow-parity.schema.json", payload)

    assert validation["ok"] is False
    assert validation["required_gaps"]


def test_shadow_accepted_difference_has_stable_shape() -> None:
    external = {
        "ok": False,
        "command": "prove",
        "state": "gapped",
        "required_gaps": ["claims_missing"],
        "data": {"repository_audit": {"required_gaps": ["claims_missing"]}},
    }
    embedded = {"ok": True, "command": "prove", "required_gaps": []}

    accepted = _accepted_semantic_differences(external, embedded)

    assert accepted == [
        {
            "kind": "external_product_repository_audit_gap",
            "classification": "accepted",
            "scope": "external_product_repository_audit",
            "commands": ["ethos prove"],
            "gaps": ["claims_missing"],
            "reason": "external product repository audit gap is not an embedded adopter parity gap",
        }
    ]


def test_parity_freshness_tracks_relevant_tree_not_evidence_touch(tmp_path: Path) -> None:
    """Parity currency follows the parity-relevant source tree, not a proxy touch of the
    evidence file. A commit that changes only parity-irrelevant paths (tests, prose)
    does NOT stale the evidence; a commit under packages/** does. This removes the
    shared-evidence-file serialization bottleneck between concurrent lanes."""

    def g(*a: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@e.x", *a],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )

    g("init", "-b", "dev")
    (tmp_path / "packages").mkdir()
    (tmp_path / "packages" / "x.py").write_text("1\n", encoding="utf-8")
    g("add", ".")
    g("commit", "-m", "product source")
    src_head = g("rev-parse", "HEAD").stdout.strip()

    # a commit touching ONLY parity-irrelevant paths must NOT stale the src head
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "t.py").write_text("t\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("prose\n", encoding="utf-8")
    g("add", ".")
    g("commit", "-m", "tests + prose (parity-irrelevant)")
    assert src_head in acceptable_parity_product_heads(tmp_path, "generic")

    # a commit under packages/** DOES stale it (verdict could change)
    (tmp_path / "packages" / "y.py").write_text("2\n", encoding="utf-8")
    g("add", ".")
    g("commit", "-m", "product source change")
    assert src_head not in acceptable_parity_product_heads(tmp_path, "generic")

    # a foreign / unrelated head is never accepted
    assert ("f" * 40) not in acceptable_parity_product_heads(tmp_path, "generic")


def test_tracked_parity_evidence_reports_absent_adopter_and_non_object_payload(
    tmp_path: Path,
) -> None:
    assert _parity_evidence(tmp_path, None) == {}
    path = tmp_path / "evidence" / "parity" / "generic-shadow.json"
    path.parent.mkdir(parents=True)
    path.write_text("[]\n", encoding="utf-8")

    report = _parity_evidence(tmp_path, "generic")

    assert report["path"] == "evidence/parity/generic-shadow.json"
    assert report["required_gaps"] == ["parity_evidence_not_object"]
    assert report["verified_capabilities"] == []


def test_parity_validation_boundary_gaps() -> None:
    payload = _complete_parity_evidence("generic")
    payload["command"] = (
        "ethos parity shadow --adopter other --target /tmp/generic --execute --json"
    )
    payload["shadow"] = "not-shadow"
    payload["verified_capabilities"] = ["not-a-capability"]
    payload["capability_basis"] = "not-basis"
    freshness = payload["freshness"]
    assert isinstance(freshness, dict)
    freshness["product_head"] = "old-product"
    freshness["target_head"] = "old-target"
    freshness["command_sha256"] = "bad-digest"

    gaps = _validate_parity_evidence(
        payload,
        "generic",
        current_product_head="new-product",
        current_target_head="new-target",
    )

    assert "parity_evidence_invalid:generic" in gaps
    assert "parity_evidence_invalid:generic:command_identity" in gaps
    assert "parity_evidence_invalid:generic:shadow" in gaps
    assert "parity_evidence_invalid:generic:unknown_capability" in gaps
    assert "parity_evidence_invalid:generic:capability_basis" in gaps
    assert "parity_evidence_invalid:generic:command_sha256" in gaps
    assert "parity_evidence_invalid:generic:product_head" in gaps
    assert "parity_evidence_invalid:generic:target_head" in gaps
    assert _command_matches_identity("ethos status --json", adopter="generic", target=None) is False
    assert (
        _command_matches_identity(
            "ethos parity shadow --adopter generic --execute --json",
            adopter="generic",
            target="/tmp/generic",
        )
        is False
    )


def test_parity_validation_accepts_repository_target_command_alias() -> None:
    assert (
        _command_matches_identity(
            "uv run --package ethos ethos parity shadow --adopter generic "
            "--target . --execute --timeout-seconds 30 --json",
            adopter="generic",
            target="<repo>",
        )
        is True
    )
    assert (
        _command_matches_identity(
            "uv run --package ethos ethos parity shadow --adopter generic "
            "--execute --timeout-seconds 30 --json",
            adopter="generic",
            target="<repo>",
        )
        is False
    )


def test_parity_validation_accepts_equivalent_heads_and_rejects_bad_capability_basis() -> None:
    payload = _complete_parity_evidence("generic")
    capabilities = payload["verified_capabilities"]
    assert isinstance(capabilities, list)
    first = capabilities[0]
    basis = payload["capability_basis"]
    assert isinstance(basis, dict)
    basis[first] = []

    gaps = _validate_parity_evidence(
        payload,
        "generic",
        current_product_head="new-product",
        current_target_head="new-target",
        acceptable_product_heads=("product-head",),
        acceptable_target_heads=("target-head",),
    )

    assert "parity_evidence_invalid:generic:product_head" not in gaps
    assert "parity_evidence_invalid:generic:target_head" not in gaps
    assert f"parity_evidence_invalid:generic:capability_basis:{first}" in gaps
