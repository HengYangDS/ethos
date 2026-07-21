"""Representative adapter edge oracles retained after coverage compression."""

from types import SimpleNamespace

import ethos.adapters.gates.signature as signature
import ethos.adapters.mutation.core as core
import ethos.adapters.mutation.lanes as lanes
import ethos.adapters.repo.status.bindings as bindings
import ethos_core.contracts.branch.roles as roles


def test_signature_gap_matrices() -> None:
    common = {"expected_identity": ("y", "y"), "allowed_identities": []}
    common["identity_mode"] = "presence"
    cases = [(("x", "x"), ["git_user_name_mismatch", "git_user_email_mismatch"]), (("y", "y"), [])]
    for actual, gaps in cases:
        assert signature._authorship_gaps(actual_identity=actual, **common) == gaps
    signing = {"gpgsign": "false", "gpg_format": "gpg", "signing_key": ""}
    signing["expected_format"] = "ssh"
    assert signature._signing_gaps(**signing) == [
        "commit_signing_disabled",
        "commit_signing_format_mismatch",
        "commit_signing_key_missing",
    ]


def test_mutation_blocker_matrices(monkeypatch, tmp_path) -> None:
    policy = SimpleNamespace(candidate_branch="candidate/dev")
    monkeypatch.setattr(core, "load_branch_role_policy", lambda _root: policy)
    monkeypatch.setattr(core, "run_git", lambda *_args, **_kwargs: SimpleNamespace(stdout="h\n"))
    monkeypatch.setattr(core, "dirty_provenance", lambda _path: {"dirty": True})
    cases = [
        ({"exists": False}, "candidate_branch_missing"),
        ({"exists": True, "worktree_exists": False}, "candidate_worktree_missing"),
        (
            {"exists": True, "worktree_exists": True, "worktree_path": "/c"},
            "candidate_worktree_dirty",
        ),
    ]
    for candidate, gap in cases:
        report = core.candidate_base_report(root=tmp_path, status={"candidate": candidate})
        assert report["required_gaps"] == [gap]
    status = {"branch": "work/x", "worktrees": [{"branch": "work/x", "role": roles.ROLE_WORK_LANE}]}
    monkeypatch.setattr(lanes, "workspace_status", lambda _root: status)
    monkeypatch.setattr(lanes, "_active_lease", lambda *_args: None)
    report = lanes.bind_work_lane_claim(root=tmp_path, claim_id="", apply=False)
    assert report["required_gaps"] == ["missing_claim_id", "work_lane_missing_lease:work/x"]
    monkeypatch.setattr(lanes, "_active_lease", lambda *_args: {"holder_ref": "agent:test:case:me"})
    report = lanes.bind_work_lane_claim(root=tmp_path, claim_id="claim", apply=False)
    assert report["state"] == "planned"


def test_branch_bindings_deduplicate_configured_and_worktree_branches(
    monkeypatch, tmp_path
) -> None:
    def binding(_root, *, branch, role, **_kwargs):
        return {"branch": branch, "role": role}

    monkeypatch.setattr(bindings, "_branch_binding", binding)
    monkeypatch.setattr(bindings, "_work_lane_refs", lambda *_args, **_kwargs: [])
    worktree = {"branch": "work/x", "role": roles.ROLE_WORK_LANE}
    policy = roles.BranchRolePolicy(release_branch="main", accepted_branch="main")
    rows = bindings.branch_bindings(
        tmp_path, [worktree, worktree], {}, policy=policy, lease_by_branch={}
    )
    assert [item["branch"] for item in rows] == ["main", "candidate/dev", "work/x"]
