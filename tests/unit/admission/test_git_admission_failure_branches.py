from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import ethos.adapters.admission.git_admission as admission
from ethos.contracts.admission import HookAdmissionRequest

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _status(role: str = "work_lane") -> dict[str, object]:
    return {"role": role, "branch": "work/example", "changed_paths": []}


def test_fallback_and_observe_only_hook_layers_are_explicit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(admission, "workspace_status", lambda *_args, **_kwargs: _status())
    fallback = admission.hook_admission_report(HookAdmissionRequest(root=tmp_path, layer="git"))
    monkeypatch.setattr(
        admission,
        "command_risk",
        lambda _command: {"unclassifiable": False, "tracked_mutation_risk": False},
    )
    monkeypatch.setattr(admission, "git_stash_policy", lambda _command: {"forbidden": False})
    observed = admission.hook_admission_report(
        HookAdmissionRequest(root=tmp_path, layer="pre-run", command="git status")
    )

    assert (fallback["state"], fallback["fallback"]) == ("fallback", True)
    assert fallback["required_gaps"] == []
    assert observed["decision"]["reason"] == "command_observe_only"


def test_stash_and_mutation_without_paths_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(admission, "workspace_status", lambda *_args, **_kwargs: _status())
    monkeypatch.setattr(
        admission,
        "command_risk",
        lambda _command: {"unclassifiable": False, "tracked_mutation_risk": True},
    )
    monkeypatch.setattr(
        admission, "git_stash_policy", lambda command: {"forbidden": command == "stash"}
    )

    stash = admission.hook_admission_report(
        HookAdmissionRequest(root=tmp_path, layer="pre-run", command="stash")
    )
    missing = admission.hook_admission_report(
        HookAdmissionRequest(root=tmp_path, layer="pre-run", command="write")
    )

    assert stash["required_gaps"] == ["git_stash_forbidden"]
    assert missing["required_gaps"] == ["hook_prerun_paths_required"]


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
    policy = SimpleNamespace(
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
    policy = SimpleNamespace(
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
