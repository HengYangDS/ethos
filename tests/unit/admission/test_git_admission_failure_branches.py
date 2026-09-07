from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.adapters.admission.git_admission as admission
from ethos.contracts.admission import HookAdmissionRequest
from ethos.contracts.branch.roles import BranchRolePolicy

if TYPE_CHECKING:
    from pathlib import Path


def _status(role: str = "work_lane") -> dict[str, object]:
    return {"role": role, "branch": "work/example", "changed_paths": []}


@pytest.mark.parametrize(
    ("layer", "command", "gap"),
    [
        ("git", "", ""),
        ("pre-run", "git status", ""),
        ("pre-run", "git stash", "git_stash_forbidden"),
        ("pre-run", "git commit", "hook_prerun_paths_required"),
        ("pre-run", "cat 'unterminated", "shell_command_unclassifiable"),
        ("unknown", "", "hook_layer_invalid"),
        ("pre-tool", "", "protected_root_pretool_paths_required"),
        ("context", "", ""),
        ("context", "foreign", "hook_context_root_mismatch"),
    ],
)
def test_hook_context_and_command_boundaries_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, layer: str, command: str, gap: str
) -> None:
    monkeypatch.setattr(admission, "workspace_status", lambda *_a, **_k: _status("accepted_root"))
    report = admission.hook_admission_report(
        HookAdmissionRequest(
            root=tmp_path,
            layer=layer,
            command=command,
            expected_root=tmp_path / "foreign" if command == "foreign" else tmp_path,
        )
    )
    assert report["verdict"] == ("block" if gap else "pass")
    assert report["required_gaps"] == ([gap] if gap else [])
    if layer == "git":
        assert (report["state"], report["fallback"]) == ("fallback", True)


def test_ref_move_policy_failure_and_noop_are_structured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        admission,
        "resolve_ref_move_policy",
        lambda *_args: (_ for _ in ()).throw(ValueError("unreadable")),
    )
    blocked = admission.ref_move_admission_report(
        root=tmp_path,
        ref_name="refs/heads/work/example",
        old_value="a" * 40,
        new_value="b" * 40,
    )
    policy = BranchRolePolicy(
        release_branch="release",
        release_mirror="none",
        candidate_branch="candidate/dev",
        accepted_branch="dev",
        work_branch_prefix="work/",
    )
    monkeypatch.setattr(admission, "resolve_ref_move_policy", lambda *_args: policy)
    noop = admission.ref_move_admission_report(
        root=tmp_path,
        ref_name="refs/heads/work/example",
        old_value="a" * 40,
        new_value="a" * 40,
    )

    assert blocked["required_gaps"] == ["ref_move_policy_unavailable"]
    assert blocked["branch"] == "work/example"
    assert noop["verdict"] == "pass"


def test_committed_intent_gap_is_repair_required(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy = BranchRolePolicy(
        release_branch="release",
        release_mirror="none",
        candidate_branch="candidate/dev",
        accepted_branch="dev",
        work_branch_prefix="work/",
    )
    monkeypatch.setattr(admission, "resolve_ref_move_policy", lambda *_args: policy)
    monkeypatch.setattr(
        admission,
        "claim_ref_intent",
        lambda **_kwargs: {"gap": "ref_intent_digest_mismatch"},
    )

    report = admission.ref_move_admission_report(
        root=tmp_path,
        ref_name="refs/heads/work/example",
        old_value="a" * 40,
        new_value="0" * 40,
        phase="committed",
    )

    assert report["state"] == "repair_required"
    assert report["required_gaps"] == ["ref_intent_digest_mismatch"]


def test_postwrite_reports_unexpected_and_outside_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outside = tmp_path.parent / "outside.txt"
    monkeypatch.setattr(
        admission,
        "workspace_status",
        lambda *_args, **_kwargs: {
            "role": "work_lane",
            "branch": "work/example",
            "changed_paths": ["outside.txt", outside.as_posix()],
        },
    )

    report = admission.hook_admission_report(
        HookAdmissionRequest(
            root=tmp_path,
            layer="post-write",
            paths=(tmp_path / "expected.txt", outside),
        )
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["post_write_unexpected_path"]
    assert report["target_paths"] == [
        (tmp_path / "expected.txt").as_posix(),
        outside.as_posix(),
    ]
    assert report["unexpected_paths"] == ["outside.txt"]
