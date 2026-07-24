from __future__ import annotations

import json
from pathlib import Path

import ethos.surface.cli.root.proof as proof_cli
from ethos.adapters.gates.runner import ActionRunResult
from ethos.repository.adoption.planner import adoption_plan
from ethos.repository.policy.schema import validate_schema_instance
from ethos_core.action_graph.core import ActionGraph
from ethos_core.contracts.branch.roles import load_branch_role_policy
from ethos_core.contracts.gates import GateDescriptor
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.ethos_cli_runner import run_ethos_raw


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
        'profile_id = "acme"\n[openspec]\nmaterial_paths = [".ethos/profile.toml"]\n\n[proof]\ncode_correctness_gates = ["acme-tests"]\n',
        encoding="utf-8",
    )

    payload = run_ethos_blocked("prove", "--root", repo.as_posix(), "--json")

    assert payload["state"] == "gapped"
    assert "adopter_gate_descriptor_missing:acme-tests" in payload["required_gaps"]
    assert "acme-tests" not in payload["data"]["gate_ids"]


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


def test_default_proof_reports_terminal_gap_without_claiming_proof() -> None:
    payload = run_ethos_blocked("prove", "--json")

    assert payload["ok"] is False
    assert payload["state"] == "gapped"
    assert any(
        gap.startswith("source_budget_terminal_exceeded:") for gap in payload["required_gaps"]
    )
    assert payload["data"]["executed"] is False
    assert {run["state"] for run in payload["data"]["evidence"]["runs"]} == {"planned"}
    assert all(run["trust_bearing"] is False for run in payload["data"]["evidence"]["runs"])
    assert "repository_audit" not in payload["data"]
    assert "provenance" not in payload["data"]


def test_default_proof_json_stays_within_payload_budget() -> None:
    completed = run_ethos_raw("prove", "--json")

    assert completed.returncode == 1
    assert len(completed.stdout.encode()) <= 32 * 1024


def test_prove_surfaces_active_archive_preflight_gap(monkeypatch) -> None:
    lifecycle = {
        "ok": False,
        "required_gaps": [
            "openspec_archive_preflight_failed:sample-change:archive_spec_update_failed"
        ],
    }
    monkeypatch.setattr(
        proof_cli,
        "openspec_governance_report",
        lambda _root, **_kwargs: lifecycle,
        raising=False,
    )

    payload = run_ethos_blocked("prove", "--scope", "change", "--json")

    assert payload["state"] == "gapped"
    assert payload["required_gaps"] == lifecycle["required_gaps"]
    assert payload["data"]["openspec_lifecycle"]["required_gaps"] == lifecycle["required_gaps"]


def test_adopter_proof_surfaces_openspec_lifecycle_gap(monkeypatch, tmp_path: Path) -> None:
    """An adopter proof cannot substitute a clean placeholder for lifecycle truth."""
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)
    git(repo, "add", ".")
    git(repo, "commit", "-m", "adopt generic profile")
    lifecycle_payload = {
        "ok": False,
        "required_gaps": ["openspec_claim_binding_missing:material-change"],
    }
    calls: list[tuple[Path, bool, tuple[str, ...]]] = []

    def report(
        root: Path,
        *,
        lifecycle: bool = False,
        changed_paths: tuple[str, ...] = (),
        **_kwargs: object,
    ) -> dict[str, object]:
        calls.append((root, lifecycle, changed_paths))
        return lifecycle_payload

    monkeypatch.setattr(proof_cli, "openspec_governance_report", report)

    payload = run_ethos_blocked("prove", "--root", repo.as_posix(), "--json")

    assert calls == [(repo, True, ())]
    assert payload["state"] == "gapped"
    assert payload["required_gaps"] == [
        *lifecycle_payload["required_gaps"],
        "adopter_profile_missing_code_correctness_gates",
    ]
    assert (
        payload["data"]["openspec_lifecycle"]["required_gaps"] == lifecycle_payload["required_gaps"]
    )


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

    payload = run_ethos("prove", "--scope", "change", "--expect-head", head, "--json")

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
    assert not (target / ".ethos" / "profile.toml").exists()


def test_adopt_apply_writes_minimal_binding_in_git_repo(tmp_path: Path) -> None:
    target = init_git_repo(tmp_path / "sample")
    head = git(target, "rev-parse", "HEAD")

    payload = run_ethos(
        "adopt",
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
    assert (target / ".ethos" / "profile.toml").exists()

    status = run_ethos("status", "--root", target.as_posix(), "--json")
    assert status["ok"] is False
    assert status["required_gaps"] == ["candidate_branch_missing"]
    assert [
        gap
        for diagnostic in status["diagnostics"]
        if diagnostic["kind"] == "schema_validation"
        for gap in diagnostic["required_gaps"]
    ] == []


def test_adopt_dry_run_does_not_write_project(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Sample\n", encoding="utf-8")

    payload = run_ethos("adopt", "--root", str(tmp_path), "--json")

    assert payload["ok"] is True
    assert payload["command"] == "adopt"
    assert payload["data"]["planned_files"] == [".ethos/profile.toml"]
    assert not (tmp_path / ".ethos").exists()


def test_adopt_apply_requires_authorization_and_expected_head(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")

    payload = run_ethos_blocked("adopt", "--root", str(repo), "--apply", "--json", cwd=repo)

    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert "authorization_required" in payload["required_gaps"]
    assert "expect_head_required" in payload["required_gaps"]
    assert not (repo / ".ethos/profile.toml").exists()


def test_adopt_apply_accepts_authorized_matching_head(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    git(repo, "config", "core.hooksPath", "existing-hooks")
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
    assert payload["summary"] == {"planned_file_count": 1}
    assert git(repo, "config", "--local", "--get", "core.hooksPath") == "existing-hooks"
    assert (repo / ".ethos/profile.toml").exists()


def test_adopt_ignores_unrelated_existing_adopter_entrypoint(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    agent_entrypoint = repo / "AGENTS.md"
    agent_entrypoint.write_text("# Existing adopter guide\n", encoding="utf-8")

    command = ("adopt", "--root", str(repo), "--apply", "--authorize")
    payload = run_ethos(*command, "--expect-head", head, "--json", cwd=repo)
    assert payload["ok"] is True
    assert payload["data"]["planned_files"] == [".ethos/profile.toml"]
    assert agent_entrypoint.read_text(encoding="utf-8") == "# Existing adopter guide\n"


def test_prove_default_floor_includes_config_and_script_quality_gates() -> None:
    payload = run_ethos_blocked("prove", "--json")

    assert payload["ok"] is False
    node_ids = payload["data"]["gate_ids"]
    assert payload["summary"]["gate_count"] == len(node_ids)
    assert {
        "evidence-freshness",
        "ruff",
        "config-quality",
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
        """profile_id = \"sample-adopter\"

[openspec]
material_paths = [\".ethos/profile.toml\"]
""",
        encoding="utf-8",
    )

    payload = run_ethos_blocked("prove", "--root", str(repo), "--json")

    assert payload["summary"]["gate_count"] == 0
    node_ids = payload["data"]["gate_ids"]
    assert node_ids == []


def test_prove_execute_can_select_real_gates(monkeypatch, tmp_path: Path) -> None:
    recorded: dict[str, object] = {}
    gate = GateDescriptor(
        id="isolated-proof",
        kind="contract",
        command=("isolated-proof",),
        evidence_class="contract",
        trust_bearing=True,
    )

    def capture_executed_proof(repo: Path, evidence: dict[str, object]) -> Path:
        recorded["repo"] = repo
        recorded["evidence"] = evidence
        return tmp_path / "proof-record.json"

    class PassingRunner:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def run(self, node, *, root: Path) -> ActionRunResult:
            assert root == tmp_path
            return ActionRunResult(
                action_id=node.id,
                command=node.command,
                state="passed",
                exit_code=0,
            )

    monkeypatch.setattr(proof_cli.git, "current_head", lambda _root: "a" * 40)
    monkeypatch.setattr(
        proof_cli.status_domain,
        "audit_for_root",
        lambda *_args, **_kwargs: {
            "ok": True,
            "required_gaps": [],
            "governance_context": {},
        },
    )
    monkeypatch.setattr(proof_cli, "workspace_status", lambda _root, **_kwargs: {})
    monkeypatch.setattr(proof_cli, "change_scope_paths_from_status", lambda *_args: ())
    monkeypatch.setattr(
        proof_cli,
        "openspec_governance_report",
        lambda *_args, **_kwargs: {"ok": True, "required_gaps": []},
    )
    monkeypatch.setattr(proof_cli, "gate_registry", lambda _root: {gate.id: gate})
    monkeypatch.setattr(
        proof_cli,
        "gate_graph",
        lambda *_args, **_kwargs: ActionGraph(nodes=(gate.to_node(),)),
    )
    monkeypatch.setattr(proof_cli, "LocalSubprocessRunner", PassingRunner)
    monkeypatch.setattr(proof_cli, "record_executed_proof", capture_executed_proof)

    run_ethos("prove", "--execute", "--root", tmp_path.as_posix(), "--json")

    assert recorded["repo"] == tmp_path
    evidence = recorded["evidence"]
    assert isinstance(evidence, dict)
    assert evidence["head"] == "a" * 40
    assert evidence["runs"][0]["state"] == "proven"
    assert evidence["runs"][0]["trust_bearing"] is True


def test_prove_execute_preserves_non_trust_bearing_gate_classification(
    monkeypatch,
) -> None:
    diagnostic_gate = GateDescriptor(
        id="diagnostic-only",
        kind="lint",
        command=("diagnostic", "--check"),
        evidence_class="diagnostic",
        trust_bearing=False,
    )

    def fake_gate_registry(root=None):
        _ = root
        return {"diagnostic-only": diagnostic_gate}

    def fake_gate_graph(gate=(), *, full, root):
        _ = gate, full, root
        return ActionGraph(nodes=(diagnostic_gate.to_node(),))

    monkeypatch.setattr(
        proof_cli,
        "gate_registry",
        fake_gate_registry,
    )
    monkeypatch.setattr(
        proof_cli,
        "gate_graph",
        fake_gate_graph,
    )

    class PassingDiagnosticRunner:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def run(self, node, *, root):
            assert root == Path.cwd()
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


def test_prove_returns_evidence_and_provenance() -> None:
    payload = run_ethos("prove", "--objective", "cli contract", "--gate", "python-size", "--json")

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
    adoption_plan(tmp_path, apply=True)

    payload = run_ethos_blocked("prove", "--root", tmp_path.as_posix(), "--json")

    assert payload["ok"] is False
    assert payload["required_gaps"] == ["adopter_profile_missing_code_correctness_gates"]
    assert "self_audit" not in payload["data"]
    assert payload["data"]["audit"]["mode"] == "repository"
    context = payload["governance_context"]
    assert context["contract"] == "governed_repository"
    assert "posture" not in context
    assert context["profile"] == "adopter"
    assert context["subject"]["kind"] == "repository"
    assert context["subject"]["id"] == str(tmp_path.resolve())
    assert context["shared_commands"] == [
        "ethos status",
        "ethos plan",
        "ethos prove",
        "ethos land",
        "ethos publish",
    ]
    assert context["transition_commands"] == [
        "ethos status",
        "ethos plan",
        "ethos prove",
        "ethos land",
        "ethos publish",
    ]
    assert context["reader_view_commands"] == ["ethos orient"]
    assert context["scorecard_commands"] == ["ethos report"]


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
    assert campaign["step_summary"]["planned"] >= 4
    assert campaign["step_summary"]["active"] == 0
    assert campaign["step_summary"]["closed"] >= 4
    assert campaign["lane_topology"]["mode"] == "strict_serial"
    assert campaign["lane_topology"]["active_step"] == ""
    assert campaign["lane_topology"]["active_steps"] == []
    assert campaign["lane_topology"]["next_planned_step"] == "projection-digest-governance"
    assert payload["data"]["publication"]["kind"] == "campaign_publication"
    assert payload["data"]["publication"]["scope"] == "repository"
    assert {
        "ordinal",
        "depends_on",
        "openspec_change",
        "work_lane",
        "claim_id",
        "closeout",
    } <= set(campaign["steps"][0])


def test_campaign_closeout_scopes_to_selected_campaign() -> None:
    payload = run_ethos(
        "campaign",
        "closeout",
        "--campaign",
        "terminal-openspec-productization",
        "--json",
    )

    assert payload["command"] == "campaign closeout"
    assert payload["summary"]["campaign"] == "terminal-openspec-productization"
    assert payload["data"]["requested_campaign"] == "terminal-openspec-productization"
    package = payload["data"]["packages"]["campaign"]
    assert package["requested_campaign"] == "terminal-openspec-productization"
    assert [item["id"] for item in package["campaigns"]] == ["terminal-openspec-productization"]


def test_campaign_status_exposes_archive_ready_retirement_without_terminal_claim() -> None:
    payload = run_ethos(
        "campaign",
        "status",
        "--campaign",
        "repo-first-worktree-governance-v2",
        "--json",
    )

    assert payload["ok"] is True
    campaign = payload["data"]["campaigns"][0]
    bootstrap = campaign["steps"][0]
    retirement = campaign["steps"][1]
    assert bootstrap["state"] == "retired"
    assert bootstrap["closeout"]["state"] == "retired"
    assert retirement["state"] == "archive_ready"
    assert retirement["closeout"]["state"] == "planned"
    assert campaign["step_summary"]["archive_ready"] == 1
    assert campaign["step_summary"]["closed"] == 1
    assert campaign["lane_topology"]["active_steps"] == ["retirement-fail-closed"]


def test_campaign_closeout_unknown_selector_reports_gap() -> None:
    payload = run_ethos(
        "campaign",
        "closeout",
        "--campaign",
        "absent-campaign",
        "--json",
    )

    assert payload["state"] == "gapped"
    assert "campaign_missing:absent-campaign" in payload["required_gaps"]
    assert payload["data"]["requested_campaign"] == "absent-campaign"
    assert payload["data"]["packages"]["campaign"]["campaigns"] == []


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
    trust_closeout = packages["trust_closeout"]
    assert (
        trust_closeout["kind"],
        trust_closeout["claim_report_ok"],
        trust_closeout["promotion_ready"],
        trust_closeout["executed_proof_evidence"],
        "work_lane_claim_binding_missing" not in " ".join(trust_closeout["required_gaps"]),
    ) == ("trust_closeout", True, True, True, True)
    assert packages["shadow_parity"]["provenance"]["mode"] == "tracked_evidence"
    assert (
        payload["data"]["provenance"]["shadow_parity"] == (packages["shadow_parity"]["provenance"])
    )
    assert payload["data"]["provenance"]["closeout"] == {
        "mode": "local_only",
        "remote_state": "deferred",
    }
    validation = validate_schema_instance("campaign-closeout.schema.json", payload["data"])
    assert validation["ok"] is True, validation["required_gaps"]
