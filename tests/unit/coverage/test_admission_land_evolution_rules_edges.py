# ruff: noqa: ARG005, FBT002, FBT003, FLY002
from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

from ethos.adapters.admission import core as admission
from ethos.domain import land
from ethos.domain import land_support
from ethos.repository.adoption import evolution
from ethos.repository.policy import rules as policy_rules
from ethos_core.contracts.branch_roles import ROLE_ACCEPTED_ROOT
from ethos_core.contracts.branch_roles import ROLE_WORK_LANE


def cp(stdout: str = "", stderr: str = "", returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(["git"], returncode, stdout, stderr)


def status(
    role: str = ROLE_WORK_LANE, dirty: bool = False, changed: list[str] | None = None
) -> dict[str, object]:
    return {
        "role": role,
        "dirty": dirty,
        "branch": "work/x" if role == ROLE_WORK_LANE else "dev",
        "changed_paths": changed or [],
        "candidate": {
            "exists": True,
            "worktree_exists": True,
            "worktree_path": "/tmp/candidate",
            "head": "c1",
        },
        "closeout_support": {"supported": True, "claim_binding": "missing", "claim_id": ""},
    }


def test_admission_hook_layers_and_postwrite_fuse(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(admission, "workspace_status", lambda repo: status())
    assert admission.hook_admission_report(root=tmp_path, layer="unknown")["state"] == "admitted"
    assert (
        admission.hook_admission_report(root=tmp_path, layer="context", expected_root=tmp_path)[
            "state"
        ]
        == "refreshed"
    )
    assert admission.hook_admission_report(
        root=tmp_path, layer="context", expected_root=tmp_path / "other"
    )["required_gaps"] == ["hook_context_root_mismatch"]
    observe = admission.hook_admission_report(root=tmp_path, layer="pre-run", command="git status")
    assert observe["decision"]["reason"] == "command_observe_only"
    risky = admission.hook_admission_report(
        root=tmp_path, layer="pre-run", command="python -c 'open(1, \"w\")'"
    )
    assert risky["required_gaps"] == ["hook_prerun_paths_required"]

    monkeypatch.setattr(
        admission,
        "workspace_status",
        lambda repo: status(ROLE_ACCEPTED_ROOT, changed=["README.md"]),
    )
    protected = admission.hook_admission_report(
        root=tmp_path, layer="post-write", paths=[Path("README.md")]
    )
    assert protected["state"] == "fused"
    assert protected["required_gaps"] == ["post_write_protected_root_dirty"]

    monkeypatch.setattr(
        admission,
        "workspace_status",
        lambda repo: status(ROLE_WORK_LANE, changed=["unexpected.md"]),
    )
    unexpected = admission.hook_admission_report(
        root=tmp_path, layer="post-write", paths=[Path("README.md")]
    )
    assert unexpected["required_gaps"] == ["post_write_unexpected_path"]


def test_push_and_ref_move_admission(monkeypatch, tmp_path: Path) -> None:
    policy = SimpleNamespace(
        accepted_branch="dev",
        role_for_branch=lambda branch: ROLE_ACCEPTED_ROOT if branch == "dev" else ROLE_WORK_LANE,
        candidate_branch="candidate/dev",
    )
    monkeypatch.setattr(
        "ethos_core.contracts.branch_roles.load_branch_role_policy", lambda root: policy
    )
    monkeypatch.setattr(
        "ethos.adapters.mutation.core._proof_gaps", lambda root, head: ["proof_not_proven"]
    )
    blocked = admission.push_admission_report(
        root=tmp_path, target_ref="refs/heads/dev", pushed_head="h1"
    )
    assert blocked["required_gaps"] == ["proof_not_proven"]
    allowed = admission.push_admission_report(
        root=tmp_path, target_ref="refs/heads/work/x", pushed_head="h1"
    )
    assert allowed["ok"] is True

    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: cp(returncode=1))
    ref = admission.ref_move_admission_report(
        root=tmp_path, ref_name="refs/heads/dev", old_value="0" * 40, new_value="h2"
    )
    assert "accepted_advance_not_candidate_validated" in ref["required_gaps"]
    noop = admission.ref_move_admission_report(
        root=tmp_path, ref_name="refs/heads/dev", old_value="h2", new_value="h2"
    )
    assert noop["ok"] is True


def test_evolution_ledger_campaign_and_candidate_edges(tmp_path: Path) -> None:
    assert evolution.evolution_ledger(tmp_path) == {"hypotheses": []}
    ledger = tmp_path / "docs" / "governance"
    ledger.mkdir(parents=True)
    (ledger / "evolution-ledger.toml").write_text("[[hypothesis]]\nid='h1'\n", encoding="utf-8")
    report = evolution.evolution_report(tmp_path)
    assert report["ok"] is False
    assert "hypothesis_missing_field:0" in report["required_gaps"]
    (ledger / "evolution-ledger.toml").write_text("[[hypothesis]\n", encoding="utf-8")
    assert "evolution_ledger_invalid_toml" in evolution.evolution_report(tmp_path)["required_gaps"]

    campaign_dir = tmp_path / "evolution" / "campaigns" / "c1"
    campaign_dir.mkdir(parents=True)
    (campaign_dir / "campaign.toml").write_text("[[bad]\n", encoding="utf-8")
    invalid = evolution.campaign_report(tmp_path)
    assert "campaign_manifest_invalid_toml:c1" in invalid["required_gaps"]
    (campaign_dir / "campaign.toml").write_text(
        "\n".join(
            [
                'id = "c1"',
                'state = "active"',
                'owner = "me"',
                'objective = "ship"',
                'claim_id = "claim"',
                "[[step]]",
                'id = "s1"',
                'title = "one"',
                'state = "active"',
                'ordinal = "bad"',
                'depends_on = ["missing"]',
                'openspec_change = "change-x"',
                'work_lane = "work/x"',
                'claim_id = "claim-s"',
            ]
        ),
        encoding="utf-8",
    )
    gaps = evolution.campaign_report(tmp_path)["required_gaps"]
    assert "campaign_step_ordinal_invalid:c1:s1" in gaps
    assert "campaign_step_dependency_not_serial:c1:s1" in gaps
    assert "campaign_step_dependency_missing:c1:s1:missing" in gaps
    assert "campaign_step_openspec_missing:c1:s1" in gaps
    assert evolution.campaign_report(tmp_path, campaign_id="missing")["required_gaps"] == [
        "campaign_missing:missing"
    ]


def test_land_readiness_projection_edges(monkeypatch, tmp_path: Path) -> None:
    assert land.command_is_executed_proof("ethos prove --execute --json") is True
    assert land.remote_publication_deferred()["state"] == "deferred"
    assert land.land_next_actions(ok=False, gaps=("candidate_base_stale",), current_head="h1")[
        0
    ].startswith("ethos lane refresh-base")
    assert land.closeout_next_actions(
        ok=False, gaps=("candidate_diverged_from_accepted",), current_head="h1"
    )[0].startswith("ethos lane candidate")

    decision = SimpleNamespace(ok=False)
    assert land.closeout_audit_root(tmp_path, decision) == tmp_path
    decision = SimpleNamespace(ok=True)
    monkeypatch.setattr(
        land,
        "workspace_status",
        lambda repo: {"candidate": {"worktree_path": str(tmp_path / "candidate")}},
    )
    assert land.closeout_audit_root(tmp_path, decision) == tmp_path / "candidate"
    skipped = land.repository_audit_after_admission(tmp_path, SimpleNamespace(ok=False))
    assert skipped["state"] == "skipped"

    assert land.intake_projection_report(tmp_path)["state"] == "unconfigured"
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "intake.toml").write_text("provider = ''\n", encoding="utf-8")
    assert land.intake_projection_report(tmp_path)["required_gaps"] == [
        "intake_provider_missing:.ethos/intake.toml"
    ]
    (tmp_path / ".ethos" / "intake.toml").write_text("bad = [\n", encoding="utf-8")
    assert land.intake_projection_report(tmp_path)["provider"] == "invalid"

    claims = {"ok": True, "claims": {}}
    workspace = {
        "role": "work_lane",
        "branch": "work/x",
        "closeout_support": {"supported": True, "claim_binding": "missing"},
    }
    gaps = land.trust_closeout_package(workspace=workspace, claims=claims)["required_gaps"]
    assert "trust_claim_missing" in gaps
    assert "work_lane_claim_binding_missing:work/x" in gaps
    envelope = {
        "promotion": {"ready": True},
        "evidence": {"commands": ["ethos prove --execute --json"]},
        "required_gaps": [],
    }
    ready = land.trust_closeout_package(
        workspace={
            "role": "work_lane",
            "branch": "work/x",
            "closeout_support": {"supported": True, "claim_binding": "bound"},
        },
        claims={"ok": True, "claims": {"c": {"trust_envelope": envelope}}},
    )
    assert ready["blocking"] is False


def test_land_support_additional_boundary_edges(monkeypatch, tmp_path: Path) -> None:
    decision = SimpleNamespace(ok=True)
    monkeypatch.setattr(
        land_support,
        "workspace_status",
        lambda _repo: {"candidate": "not-a-dict"},
    )
    assert land_support.closeout_audit_root(tmp_path, decision) == tmp_path

    (tmp_path / ".ethos").mkdir(exist_ok=True)
    (tmp_path / ".ethos" / "intake.toml").write_text('provider = "gitlab"\n', encoding="utf-8")
    configured = land_support.intake_projection_report(tmp_path)
    assert configured["state"] == "configured"
    assert configured["provider"] == "gitlab"
    assert configured["required_gaps"] == []

    blocked = land_support.trust_closeout_package(
        workspace={"role": "accepted_root", "branch": "dev"},
        claims={"ok": False, "required_gaps": ["claim_schema_invalid"], "claims": {}},
    )
    assert "claim_schema_invalid" in blocked["required_gaps"]
    assert "trust_claim_missing" in blocked["required_gaps"]


def test_rules_policy_edge_helpers_and_reports(tmp_path: Path) -> None:
    assert policy_rules._scope_matches_path("repository", "a/b") is True
    assert policy_rules._scope_matches_path("path:docs", "docs/a.md") is True
    assert policy_rules._scope_matches_path("path:", "docs/a.md") is False
    assert policy_rules._toml_value(True) == "true"
    assert policy_rules._toml_value(["a", "b"]) == '["a", "b"]'
    assert policy_rules._toml_table_key("with space") == '"with space"'
    assert policy_rules._ttl_days_or_none("7d") == 7
    assert policy_rules._ttl_days_or_none("bad") is None
    assert policy_rules._date_or_none("not-date") is None

    rules_dir = tmp_path / "rules" / "ethos"
    rules_dir.mkdir(parents=True)
    (rules_dir / "policy-exceptions.toml").write_text("[[exception]\n", encoding="utf-8")
    assert str(policy_rules.policy_exceptions_report(tmp_path)["required_gaps"][0]).startswith(
        "policy_exception_parse_error:"
    )
    (rules_dir / "policy-exceptions.toml").write_text("exception = 'bad'\n", encoding="utf-8")
    assert policy_rules.policy_exceptions_report(tmp_path)["exceptions"] == []

    config = tmp_path / ".ethos"
    config.mkdir()
    (config / "rules.toml").write_text(
        "\n".join(
            [
                "[profiles]",
                'active = ["product"]',
                "[[rule]]",
                'id = "r1"',
                'owner = "owner"',
                'authority_ref = "a"',
                'contract_ref = "c"',
                'path_globs = ["README.md"]',
                'required_gates = ["missing-gate"]',
                'severity = "blocking"',
                'stop_condition = "stop"',
                "[[rule]]",
                'id = "r1"',
                'owner = "owner"',
                'authority_ref = "a"',
                'contract_ref = "c"',
                'path_globs = ["docs/**"]',
                "required_gates = []",
                'severity = "advisory"',
                'stop_condition = "stop"',
            ]
        ),
        encoding="utf-8",
    )
    gaps = policy_rules.rules_check_report(tmp_path)["required_gaps"]
    assert "duplicate_rule_id:r1" in gaps
    assert "unknown_rule_gate:r1:missing-gate" in gaps
