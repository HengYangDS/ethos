# ruff: noqa: ARG005, FBT003, FLY002
from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import ethos.domain.land.core as land_core
import ethos.domain.land.publication as land_publication
import ethos.domain.land.trust.core as land_trust
from ethos.adapters.admission import core as admission
from ethos.adapters.repo import git as gitio
from ethos.domain.land.intake.core import intake_mine_report
from ethos.domain.land.intake.core import intake_projection_report
from ethos.repository.adoption import evolution
from ethos.repository.policy.rules.check import rules_check_report
from ethos.repository.policy.rules.evaluation import scope_matches_path
from ethos.repository.policy.rules.exceptions import date_or_none
from ethos.repository.policy.rules.exceptions import policy_exceptions_report
from ethos.repository.policy.rules.exceptions import ttl_days_or_none
from ethos.repository.policy.rules.migration import toml_table_key
from ethos.repository.policy.rules.migration import toml_value
from ethos_core.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos_core.contracts.branch.roles import ROLE_WORK_LANE
from tests.support.subprocesses import completed as cp


def status(
    role: str = ROLE_WORK_LANE, *, dirty: bool = False, changed: list[str] | None = None
) -> dict[str, object]:
    return {
        "role": role,
        "dirty": dirty,
        "branch": "work/x" if role == ROLE_WORK_LANE else "dev",
        "changed_paths": changed or [],
        "candidate": {
            "exists": True,
            "worktree_exists": True,
            "worktree_path": "/workspace/candidate",
            "head": "c1",
        },
        "closeout_support": {
            "supported": True,
            "claim_binding": "missing",
            "claim_id": "",
        },
    }


def test_admission_hook_layers_and_postwrite_fuse(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(admission, "workspace_status", lambda repo, **_kwargs: status())
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
        lambda repo, **_kwargs: status(ROLE_ACCEPTED_ROOT, changed=["README.md"]),
    )
    protected = admission.hook_admission_report(
        root=tmp_path, layer="post-write", paths=[Path("README.md")]
    )
    assert protected["state"] == "fused"
    assert protected["required_gaps"] == ["post_write_protected_root_dirty"]

    monkeypatch.setattr(
        admission,
        "workspace_status",
        lambda repo, **_kwargs: status(ROLE_WORK_LANE, changed=["unexpected.md"]),
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
        "ethos_core.contracts.branch.roles.load_branch_role_policy", lambda root: policy
    )
    monkeypatch.setattr(
        "ethos.adapters.mutation.core.proof_gaps",
        lambda root, head: ["proof_not_proven"],
    )
    blocked = admission.push_admission_report(
        root=tmp_path, target_ref="refs/heads/dev", pushed_head="h1"
    )
    # The accepted-branch push now enforces the candidate-train topology (shared with the
    # ref-move reducer via accepted_advance_gaps), so a proven-but-off-train push blocks
    # on BOTH proof and topology. On this empty tmp repo the containment check fails.
    assert "proof_not_proven" in blocked["required_gaps"]
    assert "accepted_advance_not_candidate_validated" in blocked["required_gaps"]
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
    empty_ledger = evolution.evolution_ledger(tmp_path)
    assert empty_ledger["hypotheses"] == []
    assert empty_ledger["entries"] == []
    assert empty_ledger["path"].endswith("evolution/ledger.toml")
    ledger = tmp_path / "evolution"
    ledger.mkdir(parents=True)
    (ledger / "ledger.toml").write_text("[[hypothesis]]\nid='h1'\n", encoding="utf-8")
    report = evolution.evolution_report(tmp_path)
    assert report["ok"] is False
    assert "hypothesis_missing_field:0" in report["required_gaps"]
    (ledger / "ledger.toml").write_text("[[hypothesis]\n", encoding="utf-8")
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
    assert land_trust.command_is_executed_proof("ethos prove --execute --json") is True
    assert land_publication.remote_publication_deferred()["state"] == "deferred"
    assert land_core.land_next_actions(ok=False, gaps=("candidate_base_stale",), current_head="h1")[
        0
    ].startswith("ethos lane refresh-base")
    assert land_core.closeout_next_actions(
        ok=False, gaps=("candidate_diverged_from_accepted",), current_head="h1"
    )[0].startswith("ethos lane candidate")

    decision = SimpleNamespace(ok=False)
    assert land_core.closeout_audit_root(tmp_path, decision) == tmp_path
    decision = SimpleNamespace(ok=True)
    monkeypatch.setattr(
        land_core,
        "workspace_status",
        lambda repo, **_kwargs: {"candidate": {"worktree_path": str(tmp_path / "candidate")}},
    )
    assert land_core.closeout_audit_root(tmp_path, decision) == tmp_path / "candidate"
    skipped = land_core.repository_audit_after_admission(tmp_path, SimpleNamespace(ok=False))
    assert skipped["state"] == "skipped"

    assert intake_projection_report(tmp_path)["state"] == "unconfigured"
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "intake.toml").write_text("provider = ''\n", encoding="utf-8")
    assert intake_projection_report(tmp_path)["required_gaps"] == [
        "intake_provider_missing:.ethos/intake.toml"
    ]
    (tmp_path / ".ethos" / "intake.toml").write_text("bad = [\n", encoding="utf-8")
    assert intake_projection_report(tmp_path)["provider"] == "invalid"

    claims = {"ok": True, "claims": {}}
    workspace = {
        "role": "work_lane",
        "branch": "work/x",
        "closeout_support": {"supported": True, "claim_binding": "missing"},
    }
    gaps = land_trust.trust_closeout_package(workspace=workspace, claims=claims)["required_gaps"]
    assert "trust_claim_missing" in gaps
    assert "work_lane_claim_binding_missing:work/x" in gaps
    envelope = {
        "promotion": {"ready": True},
        "evidence": {"commands": ["ethos prove --execute --json"]},
        "required_gaps": [],
    }
    ready = land_trust.trust_closeout_package(
        workspace={
            "role": "work_lane",
            "branch": "work/x",
            "closeout_support": {"supported": True, "claim_binding": "bound"},
        },
        claims={"ok": True, "claims": {"c": {"trust_envelope": envelope}}},
    )
    assert ready["blocking"] is False


def test_intake_mine_report_keeps_signals_as_non_authoritative_candidates(
    tmp_path: Path,
) -> None:
    claim_dir = tmp_path / "evidence" / "claims"
    claim_dir.mkdir(parents=True)
    (claim_dir / "alpha.toml").write_text(
        'id = "alpha"\n[evidence]\nhead = "1111111111111111111111111111111111111111"\n',
        encoding="utf-8",
    )

    report = intake_mine_report(tmp_path)

    assert report["state"] == "mined"
    assert report["repository_truth"] is False
    assert report["writes"] == []
    assert report["summary"] == {
        "signal_count": 1,
        "candidate_count": 1,
        "auto_raise_allowed": False,
        "auto_dispatch_allowed": False,
    }
    candidate = report["issue_candidates"][0]
    assert candidate["invalid_state"] == "evidence.head_stale"
    assert candidate["auto_raise_allowed"] is False
    assert candidate["auto_dispatch_allowed"] is False


def test_intake_mine_report_ignores_invalid_unbound_and_current_claims(
    tmp_path: Path, monkeypatch
) -> None:
    claims = tmp_path / "evidence" / "claims"
    claims.mkdir(parents=True)
    (claims / "bad.toml").write_text("bad = [\n", encoding="utf-8")
    (claims / "missing-evidence.toml").write_text('id = "missing-evidence"\n', encoding="utf-8")
    (claims / "blank-head.toml").write_text(
        'id = "blank-head"\n[evidence]\nhead = ""\n', encoding="utf-8"
    )
    (claims / "current-head.toml").write_text(
        'id = "current-head"\n[evidence]\nhead = "abc123"\n', encoding="utf-8"
    )
    monkeypatch.setattr(
        "ethos.domain.land.intake.core._git_head",
        lambda _repo: "abc123",
    )

    report = intake_mine_report(tmp_path)

    assert report["state"] == "clean"
    assert report["intake_envelopes"] == []
    assert report["issue_candidates"] == []


def test_intake_mine_report_uses_current_git_head_and_handles_nonzero_git(
    tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True)
    (repo / "README.md").write_text("repo\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    claims = repo / "evidence" / "claims"
    claims.mkdir(parents=True)
    (claims / "current.toml").write_text(
        f'id = "current"\n[evidence]\nhead = "{head}"\n', encoding="utf-8"
    )

    assert intake_mine_report(repo)["state"] == "clean"

    class Completed:
        returncode = 1
        stdout = ""

    monkeypatch.setattr("subprocess.run", lambda *_args, **_kwargs: Completed())

    assert intake_mine_report(repo)["state"] == "mined"


def test_intake_mine_report_tolerates_git_head_lookup_failures(tmp_path: Path, monkeypatch) -> None:
    claims = tmp_path / "evidence" / "claims"
    claims.mkdir(parents=True)
    (claims / "fallback.toml").write_text(
        'id = "fallback"\n[evidence]\nhead = "abc123"\n', encoding="utf-8"
    )

    def raise_os_error(*_args, **_kwargs):
        raise OSError

    monkeypatch.setattr("subprocess.run", raise_os_error)

    report = intake_mine_report(tmp_path)

    assert report["state"] == "mined"
    assert report["issue_candidates"][0]["candidate_id"] == "claim-fallback-head-fallback"


def test_land_publication_additional_boundary_edges(monkeypatch, tmp_path: Path) -> None:
    decision = SimpleNamespace(ok=True)
    monkeypatch.setattr(
        land_core,
        "workspace_status",
        lambda _repo, **_kwargs: {"candidate": "not-a-dict"},
    )
    assert land_core.closeout_audit_root(tmp_path, decision) == tmp_path

    (tmp_path / ".ethos").mkdir(exist_ok=True)
    (tmp_path / ".ethos" / "intake.toml").write_text('provider = "gitlab"\n', encoding="utf-8")
    configured = intake_projection_report(tmp_path)
    assert configured["state"] == "configured"
    assert configured["provider"] == "gitlab"
    assert configured["required_gaps"] == []

    blocked = land_trust.trust_closeout_package(
        workspace={"role": "accepted_root", "branch": "dev"},
        claims={"ok": False, "required_gaps": ["claim_schema_invalid"], "claims": {}},
    )
    assert "claim_schema_invalid" in blocked["required_gaps"]
    assert "trust_claim_missing" in blocked["required_gaps"]


def test_rules_policy_edge_helpers_and_reports(tmp_path: Path) -> None:
    assert scope_matches_path("repository", "a/b") is True
    assert scope_matches_path("path:docs", "docs/a.md") is True
    assert scope_matches_path("path:", "docs/a.md") is False
    assert toml_value(True) == "true"
    assert toml_value(["a", "b"]) == '["a", "b"]'
    assert toml_table_key("with space") == '"with space"'
    assert ttl_days_or_none("7d") == 7
    assert ttl_days_or_none("bad") is None
    assert date_or_none("not-date") is None

    rules_dir = tmp_path / "rules" / "ethos"
    rules_dir.mkdir(parents=True)
    (rules_dir / "policy-exceptions.toml").write_text("[[exception]\n", encoding="utf-8")
    assert str(policy_exceptions_report(tmp_path)["required_gaps"][0]).startswith(
        "policy_exception_parse_error:"
    )
    (rules_dir / "policy-exceptions.toml").write_text("exception = 'bad'\n", encoding="utf-8")
    assert policy_exceptions_report(tmp_path)["exceptions"] == []

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
    gaps = rules_check_report(tmp_path)["required_gaps"]
    assert "duplicate_rule_id:r1" in gaps
    assert "unknown_rule_gate:r1:missing-gate" in gaps


def test_remote_availability_and_local_ci_fallback_edges(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_run(args, **_kwargs):
        calls.append(tuple(args))
        if args[:3] == ["git", "remote", "get-url"]:
            return cp(stdout="https://example.invalid/repo.git\n")
        if args[:3] == ["git", "ls-remote", "--exit-code"]:
            return cp(stderr="network down", returncode=128)
        return cp(returncode=1)

    monkeypatch.setattr(subprocess, "run", fake_run)
    availability = gitio.remote_availability(tmp_path)

    assert availability["state"] == "unavailable"
    assert availability["available"] is False
    assert availability["blocking"] is False
    assert availability["required_gaps"] == []
    assert availability["advisory_gaps"] == ["remote_unavailable:origin"]
    assert ("git", "ls-remote", "--exit-code", "origin") in calls

    deferred = land_publication.remote_publication_deferred(availability)
    assert deferred["state"] == "deferred"
    assert deferred["fallback"]["kind"] == "local_ci_fallback"
    assert deferred["fallback"]["hosted_ci_status_claimed"] is False

    package = land_publication.publication_readiness(
        branch="work/x",
        local_ok=True,
        policy=SimpleNamespace(submit_branch_for_source=lambda branch: f"submit/{branch}"),
        remote_availability=availability,
    )
    assert package["remote_state"] == "deferred"
    assert package["fallback_evidence"]["evidence_class"] == "local_fallback"
    assert package["fallback_evidence"]["command"] == "tools/ci/scripts/run-local-ci.sh"
    assert "tools/ci/scripts/run-module-layout.sh" in package["fallback_evidence"]["owner_scripts"]
    assert package["required_gaps"] == []
    assert package["next_actions"] == [
        "run tools/ci/scripts/run-local-ci.sh as local fallback evidence"
    ]


def test_remote_availability_reports_configured_remote_available(
    monkeypatch, tmp_path: Path
) -> None:
    def fake_run(args, **_kwargs):
        if args[:3] == ["git", "remote", "get-url"]:
            return cp(stdout="git@example.invalid:repo.git\n")
        if args[:3] == ["git", "ls-remote", "--exit-code"]:
            return cp(stdout="abc\tHEAD\n")
        return cp(returncode=1)

    monkeypatch.setattr(subprocess, "run", fake_run)
    availability = gitio.remote_availability(tmp_path)

    assert availability["state"] == "available"
    assert availability["available"] is True
    package = land_publication.publication_readiness(
        branch="work/x",
        local_ok=True,
        policy=SimpleNamespace(submit_branch_for_source=lambda branch: f"submit/{branch}"),
        remote_availability=availability,
    )
    assert package["remote_state"] == "deferred"
    assert package["remote_availability"]["state"] == "available"
    assert package["next_actions"] == [
        "create configured submit branch when remote publication is available"
    ]
