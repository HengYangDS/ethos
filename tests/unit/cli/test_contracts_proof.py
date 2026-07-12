from __future__ import annotations

import json
from pathlib import Path

from ethos.repository.adoption.planner import adoption_plan
from ethos.repository.policy.schema import validate_schema_instance
from ethos_core.contracts.branch.roles import load_branch_role_policy
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked


def test_full_proof_requires_executed_evidence() -> None:
    payload = run_ethos_blocked("prove", "--full", "--json")

    assert payload["ok"] is False
    assert payload["state"] == "gapped"
    assert "full_proof_requires_execute" in payload["required_gaps"]


def test_prove_gapped_audit_points_to_real_audit_command(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "bad.md").write_text(
        """---
subject: sample:bad
role: reference
state: active
relations:
  see_also: []
---

# Bad

Status: active.

Purpose: trigger a docs gap.

See also: none.

```bash
proof legacy objective
```
""",
        encoding="utf-8",
    )

    payload = run_ethos_blocked("prove", "--root", tmp_path.as_posix(), "--json")

    assert payload["ok"] is False
    assert payload["state"] == "gapped"
    assert payload["next_actions"] == ["ethos audit --mode deep"]


def test_prove_missing_gate_dependency_reports_concrete_rerun(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")

    payload = run_ethos_blocked(
        "prove",
        "--root",
        repo.as_posix(),
        "--gate",
        "openspec",
        "--json",
    )

    assert payload["ok"] is False
    assert "missing_dependency:openspec->schemas" in payload["required_gaps"]
    assert payload["next_actions"] == [
        f"ethos prove --execute --gate schemas --gate openspec --expect-head {head} --json"
    ]


def test_adopter_id_only_gate_declaration_fails_closed_without_traceback(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    (repo / ".ethos").mkdir(exist_ok=True)
    (repo / ".ethos/profile.toml").write_text(
        'profile_id = "acme"\n[proof]\ncode_correctness_gates = ["acme-tests"]\n',
        encoding="utf-8",
    )

    payload = run_ethos_blocked("prove", "--root", repo.as_posix(), "--json")

    assert payload["state"] == "gapped"
    assert "adopter_gate_descriptor_missing:acme-tests" in payload["required_gaps"]
    assert "acme-tests" not in [node["id"] for node in payload["data"]["action_graph"]["nodes"]]


def test_executed_proof_blocks_ethos_json_gate_failures(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text(
        "---\nsubject: sample:guide\nrole: how-to\nstate: active\nrelations: {}\n---\n\n# Guide\n\nBody without required visible sections.",
        encoding="utf-8",
    )

    payload = run_ethos_blocked(
        "prove",
        "--execute",
        "--gate",
        "docs-registry",
        "--root",
        tmp_path.as_posix(),
        "--json",
    )

    assert payload["ok"] is False
    assert payload["state"] == "gapped"
    run = payload["data"]["evidence"]["runs"][0]
    assert run["action_id"] == "docs-registry"
    assert run["state"] == "blocked"
    assert run["verdict"] == "failed"
    assert run["diagnostics"][0]["required_gaps"] == [
        "missing_visible_section:docs/guide.md:status",
        "missing_visible_section:docs/guide.md:purpose",
        "missing_visible_section:docs/guide.md:see also",
    ]


def test_default_proof_reports_readiness_not_proven() -> None:
    payload = run_ethos("prove", "--json")

    assert payload["ok"] is True
    assert payload["state"] == "ready"
    assert payload["data"]["executed"] is False
    assert {run["state"] for run in payload["data"]["evidence"]["runs"]} == {"planned"}
    assert all(run["trust_bearing"] is False for run in payload["data"]["evidence"]["runs"])


def test_prove_accepts_proof_scope_compatibility_flag() -> None:
    payload = run_ethos("prove", "--scope", "proof-kernel", "--json")

    assert payload["ok"] is True
    assert payload["state"] == "ready"
    assert payload["data"]["scope"] == "proof-kernel"
    assert payload["data"]["scope_binding"]["accepted"] is True
    assert payload["data"]["scope_binding"]["known"] is True


def test_prove_accepts_host_probe_compatibility_flags_without_claiming_host_truth() -> None:
    payload = run_ethos(
        "prove",
        "--scope",
        "proof-kernel",
        "--host",
        "--probe",
        "--json",
    )

    assert payload["ok"] is True
    assert payload["state"] == "ready"
    assert payload["data"]["scope"] == "proof-kernel"
    host_probe = payload["data"]["host_probe"]
    assert host_probe["requested"] is True
    assert host_probe["host"] is True
    assert host_probe["probe"] is True
    assert host_probe["satisfies_repository_proof"] is False


def test_prove_rejects_unknown_proof_scope() -> None:
    payload = run_ethos_blocked("prove", "--scope", "unknown-scope", "--json")

    assert payload["ok"] is False
    assert payload["state"] == "gapped"
    assert "unknown_proof_scope:unknown-scope" in payload["required_gaps"]
    assert payload["data"]["scope_binding"]["accepted"] is False


def test_prove_accepts_matching_expected_head() -> None:
    head = git(Path.cwd(), "rev-parse", "HEAD")

    payload = run_ethos("prove", "--expect-head", head, "--json")

    assert payload["ok"] is True
    assert payload["state"] == "ready"
    assert payload["required_gaps"] == []
    assert payload["data"]["expected_head"] == {
        "expected": head,
        "current": head,
        "ok": True,
    }


def test_prove_rejects_mismatched_expected_head() -> None:
    payload = run_ethos_blocked("prove", "--expect-head", "not-the-current-head", "--json")

    assert payload["ok"] is False
    assert payload["state"] == "gapped"
    assert "expected_head_mismatch" in payload["required_gaps"]
    assert payload["data"]["expected_head"]["expected"] == "not-the-current-head"
    assert payload["data"]["expected_head"]["ok"] is False


def test_prove_rejects_mismatched_expected_head_with_nonzero_exit() -> None:
    payload = run_ethos_blocked("prove", "--expect-head", "not-the-current-head", "--json")

    assert payload["ok"] is False
    assert payload["state"] == "gapped"
    assert "expected_head_mismatch" in payload["required_gaps"]
    assert payload["data"]["expected_head"]["expected"] == "not-the-current-head"
    assert payload["data"]["expected_head"]["ok"] is False


def test_init_apply_rejects_untracked_expected_head(tmp_path: Path) -> None:
    target = tmp_path / "sample"
    target.mkdir()

    payload = run_ethos_blocked(
        "init",
        "--root",
        target.as_posix(),
        "--apply",
        "--authorize",
        "--expect-head",
        "untracked",
        "--json",
    )

    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert "git_repository_missing" in payload["required_gaps"]
    assert not (target / ".ethos" / "project.toml").exists()

    assert payload["data"]["mutation"] == {
        "apply": True,
        "authorized": True,
        "expect_head": "untracked",
        "current_head": "untracked",
    }


def test_adopt_apply_rejects_untracked_expected_head(tmp_path: Path) -> None:
    target = tmp_path / "sample"
    target.mkdir()

    payload = run_ethos_blocked(
        "adopt",
        "--root",
        target.as_posix(),
        "--apply",
        "--authorize",
        "--expect-head",
        "untracked",
        "--json",
    )

    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert "git_repository_missing" in payload["required_gaps"]
    assert not (target / ".ethos" / "project.toml").exists()


def test_init_apply_flag_applies_scaffold_in_git_repo(tmp_path: Path) -> None:
    target = init_git_repo(tmp_path / "sample")
    head = git(target, "rev-parse", "HEAD")

    payload = run_ethos(
        "init",
        "--root",
        target.as_posix(),
        "--apply",
        "--authorize",
        "--expect-head",
        head,
        "--json",
    )

    assert payload["ok"] is True
    assert payload["state"] == "applied"
    assert (target / ".ethos" / "project.toml").exists()

    status = run_ethos("status", "--root", target.as_posix(), "--json")
    docs = run_ethos("quality", "docs-registry", "--root", target.as_posix(), "--json")
    examples = run_ethos(
        "quality",
        "command-examples",
        "--root",
        target.as_posix(),
        "--json",
    )

    assert status["ok"] is True
    assert [
        gap
        for diagnostic in status["diagnostics"]
        if diagnostic["kind"] == "schema_validation"
        for gap in diagnostic["required_gaps"]
    ] == []
    assert docs["ok"] is True
    assert examples["ok"] is True


def test_adopt_dry_run_does_not_write_project(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Sample\n", encoding="utf-8")

    payload = run_ethos("adopt", "--root", str(tmp_path), "--dry-run", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "adopt"
    assert ".ethos/project.toml" in payload["data"]["planned_files"]
    assert not (tmp_path / ".ethos").exists()


def test_adopt_apply_requires_authorization_and_expected_head(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")

    payload = run_ethos_blocked("adopt", "--root", str(repo), "--apply", "--json", cwd=repo)

    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert "authorization_required" in payload["required_gaps"]
    assert "expect_head_required" in payload["required_gaps"]
    assert not (repo / ".ethos/project.toml").exists()


def test_adopt_apply_accepts_authorized_matching_head(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")

    payload = run_ethos(
        "adopt",
        "--root",
        str(repo),
        "--apply",
        "--authorize",
        "--expect-head",
        head,
        "--json",
        cwd=repo,
    )

    assert payload["ok"] is True
    assert payload["state"] == "applied"
    assert payload["data"]["mutation"] == {
        "apply": True,
        "authorized": True,
        "expect_head": head,
        "current_head": head,
    }
    assert (repo / ".ethos/project.toml").exists()


def test_adopt_overlay_apply_preserves_existing_adopter_entrypoint(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    agent_entrypoint = repo / "AGENTS.md"
    agent_entrypoint.write_text("# Existing adopter guide\n", encoding="utf-8")

    command = ("adopt", "--root", str(repo), "--overlay", "--apply", "--authorize")
    payload = run_ethos(*command, "--expect-head", head, "--json", cwd=repo)
    assert payload["ok"] is True
    assert payload["data"]["mode"] == "overlay"
    assert payload["data"]["preserved_files"][0]["path"] == "AGENTS.md"
    assert agent_entrypoint.read_text(encoding="utf-8") == "# Existing adopter guide\n"


def test_prove_default_floor_includes_config_and_script_quality_gates() -> None:
    payload = run_ethos("prove", "--json")

    assert payload["ok"] is True
    node_ids = [node["id"] for node in payload["data"]["action_graph"]["nodes"]]
    assert payload["summary"]["gate_count"] == len(node_ids)
    assert {
        "evidence-freshness",
        "ruff",
        "toml-config",
        "yaml-config",
        "shell-lint",
        "format-policy",
        "generated-artifacts",
        "docs-topology",
        "python-size",
    } <= set(node_ids)


def test_prove_uses_adopter_profile_default_floor(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    profile = repo / ".ethos" / "profile.toml"
    profile.parent.mkdir(exist_ok=True)
    profile.write_text(
        """schema_version = 1
profile_id = \"sample-adopter\"
profile_version = \"1\"
ethos_contract_version = \"1\"

[repository]
kind = \"software\"
root_subject = \"sample\"
""",
        encoding="utf-8",
    )

    payload = run_ethos_blocked("prove", "--root", str(repo), "--json")

    assert payload["summary"]["gate_count"] == 11
    node_ids = [node["id"] for node in payload["data"]["action_graph"]["nodes"]]
    assert set(node_ids) == {
        "repository-audit",
        "claims",
        "evidence-freshness",
        "docs-topology",
        "schemas",
        "playbooks-v2",
        "generated-artifacts",
        "format-policy",
        "asset-determinism",
        "schema-contracts",
        "proof-policy",
    }
    assert "ruff" not in node_ids
    assert "unit-architecture" not in node_ids
    assert "docstrings" not in node_ids


def test_prove_execute_can_select_real_gates(monkeypatch, tmp_path: Path) -> None:
    import ethos.surface.cli.root.proof as proof_cli

    recorded: dict[str, object] = {}

    def capture_executed_proof(repo: Path, evidence: dict[str, object]) -> Path:
        recorded["repo"] = repo
        recorded["evidence"] = evidence
        return tmp_path / "proof-record.json"

    monkeypatch.setattr(proof_cli, "record_executed_proof", capture_executed_proof)
    payload = run_ethos(
        "prove",
        "--execute",
        "--gate",
        "repository-audit",
        "--gate",
        "claims",
        "--json",
    )

    assert payload["ok"] is True
    assert payload["state"] == "proven"
    assert payload["data"]["executed"] is True
    assert payload["summary"]["gate_count"] == 2
    assert {run["state"] for run in payload["data"]["evidence"]["runs"]} == {"proven"}
    assert {run["verdict"] for run in payload["data"]["evidence"]["runs"]} == {"passed"}
    assert all(run["trust_bearing"] is True for run in payload["data"]["evidence"]["runs"])
    assert recorded == {"repo": Path.cwd(), "evidence": payload["data"]["evidence"]}


def test_prove_execute_preserves_non_trust_bearing_gate_classification(
    monkeypatch,
) -> None:
    import ethos.surface.cli.root.proof as proof_cli
    from ethos.adapters.gates.runner import ActionRunResult
    from ethos_core.action_graph.core import ActionGraph
    from ethos_core.contracts.gates import GateDescriptor

    diagnostic_gate = GateDescriptor(
        id="diagnostic-only",
        kind="lint",
        command=("diagnostic", "--check"),
        evidence_class="diagnostic",
        trust_bearing=False,
    )
    monkeypatch.setattr(
        proof_cli,
        "gate_registry",
        lambda root=None: {"diagnostic-only": diagnostic_gate},  # noqa: ARG005
    )
    monkeypatch.setattr(
        proof_cli,
        "gate_graph",
        lambda gate=(), full=False, root=None: ActionGraph(nodes=(diagnostic_gate.to_node(),)),  # noqa: ARG005
    )

    class PassingDiagnosticRunner:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def run(self, node, *, root):
            return ActionRunResult(
                action_id=node.id,
                command=node.command,
                state="passed",
                exit_code=0,
                stdout="",
                stderr="",
            )

    monkeypatch.setattr(proof_cli, "LocalSubprocessRunner", PassingDiagnosticRunner)

    payload = run_ethos_blocked(
        "prove",
        "--execute",
        "--gate",
        "diagnostic-only",
        "--json",
    )

    assert payload["ok"] is False
    assert payload["state"] == "gapped"
    assert "trust_bearing_proof_missing" in payload["required_gaps"]
    assert payload["summary"]["gate_count"] == 1
    run = payload["data"]["evidence"]["runs"][0]
    assert run["action_id"] == "diagnostic-only"
    assert run["state"] == "executed"
    assert run["verdict"] == "passed"
    assert run["evidence_class"] == "diagnostic"
    assert run["trust_bearing"] is False


def test_adopt_gitlab_profile_is_available(tmp_path: Path) -> None:
    payload = run_ethos(
        "adopt",
        "--root",
        str(tmp_path),
        "--profile",
        "gitlab",
        "--dry-run",
        "--json",
    )

    assert payload["ok"] is True
    assert payload["data"]["profile"] == "gitlab"
    assert ".gitlab-ci.yml" in payload["data"]["planned_files"]


def test_prove_returns_evidence_and_provenance() -> None:
    payload = run_ethos("prove", "--objective", "cli contract", "--json")

    assert payload["ok"] is True
    assert payload["data"]["evidence"]["digest"]
    assert (
        payload["data"]["governance_context"]
        == payload["data"]["repository_audit"]["governance_context"]
    )
    assert payload["data"]["governance_context"]["single_kernel"] is True
    assert (
        payload["data"]["provenance"]["subject"][0]["digest"]["sha256"]
        == (payload["data"]["evidence"]["digest"])
    )


def test_prove_uses_repository_audit_for_non_product_repo(tmp_path: Path) -> None:
    adoption_plan(tmp_path, profile="generic", apply=True)

    payload = run_ethos("prove", "--root", tmp_path.as_posix(), "--json")

    assert payload["ok"] is True
    assert "self_audit" not in payload["data"]
    assert payload["data"]["repository_audit"]["mode"] == "repository"
    assert (
        payload["data"]["governance_context"]
        == payload["data"]["repository_audit"]["governance_context"]
    )
    assert payload["data"]["governance_context"]["contract"] == "governed_repository"
    assert payload["data"]["repository_audit"]["governance_context"]["contract"] == (
        "governed_repository"
    )
    assert "posture" not in payload["data"]["governance_context"]
    assert "posture" not in payload["data"]["repository_audit"]["governance_context"]
    assert payload["data"]["repository_audit"]["governance_context"]["profile"] == "generic"
    assert (
        payload["data"]["repository_audit"]["governance_context"]["subject"]["kind"] == "repository"
    )
    assert payload["data"]["repository_audit"]["governance_context"]["subject"]["id"] == str(
        tmp_path.resolve()
    )
    assert payload["data"]["repository_audit"]["governance_context"]["shared_commands"] == [
        "ethos status",
        "ethos plan",
        "ethos prove",
        "ethos land",
        "ethos publish",
    ]
    assert payload["data"]["repository_audit"]["governance_context"]["transition_commands"] == [
        "ethos status",
        "ethos plan",
        "ethos prove",
        "ethos land",
        "ethos publish",
    ]
    assert payload["data"]["repository_audit"]["governance_context"]["reader_view_commands"] == [
        "ethos orient"
    ]
    assert payload["data"]["repository_audit"]["governance_context"]["scorecard_commands"] == [
        "ethos report",
    ]


def test_projection_drift_reports_registry_and_generator_digest_state() -> None:
    payload = run_ethos("quality", "projection-drift", "--json")

    assert payload["ok"] is True
    assert payload["data"]["registry"]["digest"].startswith("sha256:")
    assert payload["data"]["registry"]["expected_digest"].startswith("sha256:")
    assert payload["data"]["registry"]["ok"] is True
    assert payload["data"]["generator"]["digest"].startswith("sha256:")
    assert payload["data"]["generator"]["expected_digest"].startswith("sha256:")
    assert payload["data"]["generator"]["ok"] is True
    assert payload["data"]["inputs"][0]["path"] == ".agents/skills/activation.toml"
    assert payload["data"]["inputs"][0]["digest"].startswith("sha256:")


def test_campaign_hypotheses_are_visible() -> None:
    payload = run_ethos("campaign", "hypotheses", "--json")

    assert payload["ok"] is True
    assert payload["data"]["hypotheses"]


def test_campaign_status_reports_manifest_steps() -> None:
    payload = run_ethos("campaign", "status", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "campaign status"
    assert payload["summary"]["active_campaign_count"] >= 1
    assert payload["data"]["campaigns"]
    campaign = next(
        item
        for item in payload["data"]["campaigns"]
        if item["id"] == "terminal-openspec-productization"
    )
    assert campaign["step_summary"]["total"] >= 8
    assert campaign["step_summary"]["planned"] >= 5
    assert campaign["step_summary"]["active"] == 0
    assert campaign["step_summary"]["closed"] >= 4
    assert campaign["lane_topology"]["mode"] == "strict_serial"
    assert campaign["lane_topology"]["active_step"] == ""
    assert campaign["lane_topology"]["active_steps"] == []
    assert campaign["lane_topology"]["next_planned_step"] == "adopter-openspec-scaffold"
    assert {
        "ordinal",
        "depends_on",
        "openspec_change",
        "work_lane",
        "claim_id",
        "closeout",
    } <= set(campaign["steps"][0])


def test_campaign_closeout_reports_local_campaign_packages() -> None:
    branch = git(Path.cwd(), "branch", "--show-current") or "detached"
    expected_submit = load_branch_role_policy(Path.cwd()).submit_branch_for_source(branch)
    evidence = json.loads(Path("evidence/parity/generic-shadow.json").read_text(encoding="utf-8"))
    target = Path.cwd() if evidence.get("target") == "<repo>" else Path(str(evidence["target"]))

    payload = run_ethos(
        "campaign",
        "closeout",
        "--adopter",
        "generic",
        "--target",
        target.as_posix(),
        "--json",
    )

    assert payload["command"] == "campaign closeout"
    assert payload["state"] in {"local_ready", "gapped"}
    assert payload["summary"]["remote_state"] == "deferred"
    assert payload["summary"]["parity_pending_count"] == len(
        payload["data"]["parity"]["pending_packages"]
    )
    remote_publication = payload["data"]["remote_publication"]
    assert remote_publication["remote_push"] == "not_performed"
    assert remote_publication["state"] == "deferred"
    assert remote_publication["reason"] in {
        "remote publication adapter unavailable",
        "remote unavailable; use local-ci fallback evidence",
    }
    assert remote_publication["availability"]["blocking"] is False
    assert remote_publication["fallback"]["kind"] == "local_ci_fallback"
    assert remote_publication["fallback"]["hosted_ci_status_claimed"] is False

    packages = payload["data"]["packages"]
    assert set(packages) == {
        "local_closeout",
        "trust_closeout",
        "campaign",
        "intake_projection",
        "publication",
        "release",
        "parity",
        "shadow_parity",
    }
    assert packages["local_closeout"]["target_branch"] == "candidate/dev"
    assert packages["campaign"]["kind"] == "campaign_closeout"
    assert packages["campaign"]["active_count"] >= 1
    assert packages["campaign"]["campaigns"]
    assert (
        packages["local_closeout"]["required_gaps"]
        == payload["data"]["workspace"]["closeout_support"]["required_gaps"]
    )
    assert packages["publication"]["remote_push"] == "not_performed"
    assert packages["publication"]["local_submit_package"]["source_branch"] == branch
    assert packages["publication"]["local_submit_package"]["submit_branch"] == expected_submit
    assert packages["release"]["ok"] is True
    assert packages["parity"]["pending_count"] == len(payload["data"]["parity"]["pending_packages"])
    assert packages["parity"]["pending_count"] == payload["summary"]["parity_pending_count"]
    assert packages["parity"]["blocking"] is False
    assert packages["parity"]["required_gaps"] == payload["data"]["parity"]["required_gaps"]
    if payload["data"]["parity"]["required_gaps"]:
        assert "parity_evidence_invalid:generic" in payload["data"]["parity"]["required_gaps"]
    if payload["state"] == "gapped" and not payload["data"]["parity"]["required_gaps"]:
        assert any(
            package.get("required_gaps")
            for package in packages.values()
            if isinstance(package, dict)
        )
    assert packages["shadow_parity"] == payload["data"]["shadow_parity"]["execution_packages"][0]
    assert packages["shadow_parity"]["state"] in {"matched", "invalid", "not_run"}
    assert packages["shadow_parity"]["evidence_path"] == ("evidence/parity/generic-shadow.json")
    assert packages["shadow_parity"]["blocking"] == bool(packages["shadow_parity"]["required_gaps"])
    assert packages["intake_projection"]["kind"] == "intake_projection"
    assert packages["intake_projection"]["truth_boundary"] == "projection-evidence"
    assert packages["trust_closeout"]["kind"] == "trust_closeout"
    assert packages["trust_closeout"]["claim_report_ok"] is True
    assert packages["trust_closeout"]["promotion_ready"] is True
    assert packages["trust_closeout"]["executed_proof_evidence"] is True
    assert packages["shadow_parity"]["provenance"]["mode"] == "tracked_evidence"
    assert (
        payload["data"]["provenance"]["shadow_parity"] == (packages["shadow_parity"]["provenance"])
    )
    assert payload["data"]["provenance"]["closeout"] == {
        "mode": "local_only",
        "remote_state": "deferred",
    }
    validation = validate_schema_instance("campaign-closeout.schema.json", payload["data"])
    assert validation["ok"] is True


def test_init_command_is_adoption_alias_without_writing(tmp_path: Path) -> None:
    payload = run_ethos("init", "--root", str(tmp_path), "--dry-run", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "init"
    assert "openspec/config.yaml" in payload["data"]["planned_files"]
    assert ".agents/skills/activation.toml" in payload["data"]["planned_files"]
    assert not (tmp_path / ".ethos").exists()
