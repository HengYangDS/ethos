from __future__ import annotations

from datetime import UTC
from datetime import datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

import pytest

import ethos.adapters.mutation.lane_lifecycle.work_lane_refresh as refresh
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import compile_git_effect_plan
from ethos.contracts.semantic import Facts
from tests.support.semantic import commitment_fixture

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


HEAD = "a" * 40
CANDIDATE = "b" * 40
REBASED = "c" * 40
BRANCH = "work/feature"


def _completed(*, returncode: int = 0, stdout: str = "", stderr: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def _status(*, branch: str = BRANCH) -> dict[str, Any]:
    return {
        "branch": branch,
        "role": ROLE_WORK_LANE,
        "dirty": False,
        "candidate": {
            "exists": True,
            "worktree_exists": True,
            "head": CANDIDATE,
            "worktree_path": "/candidate",
        },
    }


def _common(monkeypatch: pytest.MonkeyPatch, *, branch: str = BRANCH) -> None:
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test")
    monkeypatch.setattr(
        refresh,
        "load_branch_role_policy",
        lambda _root: SimpleNamespace(candidate_branch="candidate/dev"),
    )
    monkeypatch.setattr(refresh, "workspace_status", lambda _root: _status(branch=branch))
    monkeypatch.setattr(refresh, "changed_paths", lambda _path: ())
    monkeypatch.setattr(
        refresh,
        "run_git",
        lambda _root, *args, **_kwargs: _completed(
            stdout=(HEAD if args[-2:] == ("rev-parse", "HEAD") else CANDIDATE) + "\n"
        ),
    )


def _recovery_plan(
    *,
    updates: dict[str, GitRefUpdate] | None = None,
    execution_branch: str = BRANCH,
):
    effect = GitEffect(
        updates=updates or {f"refs/heads/{BRANCH}": GitRefUpdate(expected=HEAD, desired=REBASED)},
        assertions={"refs/heads/candidate/dev": CANDIDATE},
    )
    return compile_git_effect_plan(
        commitment_fixture(
            id="authority:test:refresh",
            intent="Recover one refresh effect.",
            subjects=("repository:test",),
        ),
        Facts(
            repository="repository:test",
            head=REBASED,
            tree="f" * 40,
            observed_at=datetime(2026, 8, 10, tzinfo=UTC),
            values={
                "refs": {name: update.expected for name, update in effect.updates.items()},
                "assertions": effect.assertions,
            },
        ),
        prior_attestations={},
        policy={"operation": "lane.refresh", "execution_branch": execution_branch},
        effect=effect,
    )


def _stub_refresh_effect(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        refresh,
        "load_repository_commitment",
        lambda *_args, **_kwargs: SimpleNamespace(id="repository:self", digest=lambda: "d" * 64),
    )
    monkeypatch.setattr(refresh, "lease_generation", lambda _lease: {})
    monkeypatch.setattr(refresh, "leases_by_branch", lambda _root: {BRANCH: {}})
    monkeypatch.setattr(
        refresh,
        "compile_observed_git_effect",
        lambda *_args, **_kwargs: SimpleNamespace(digest="plan-digest"),
    )
    monkeypatch.setattr(
        refresh,
        "issue_native_effect",
        lambda *_args, **_kwargs: SimpleNamespace(model_dump=lambda **_kwargs: {}),
    )


def test_refresh_public_reader_distinguishes_current_and_ready(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _common(monkeypatch)
    monkeypatch.setattr(refresh, "is_ancestor", lambda *_args: True)
    current = refresh.refresh_work_lane_base(root=tmp_path)
    assert current["state"] == "base_current"

    monkeypatch.setattr(refresh, "is_ancestor", lambda *_args: False)
    ready = refresh.refresh_work_lane_base(root=tmp_path)
    assert ready["state"] == "ready_to_refresh_base"


@pytest.mark.parametrize(
    ("candidate", "gap"),
    [
        ({"exists": False, "worktree_exists": False}, "candidate_branch_missing"),
        ({"exists": True, "worktree_exists": False}, "candidate_worktree_missing"),
        ({"exists": True, "worktree_exists": True}, "candidate_worktree_dirty"),
    ],
)
def test_refresh_public_reader_reports_candidate_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    candidate: dict[str, object],
    gap: str,
) -> None:
    _common(monkeypatch)
    monkeypatch.setattr(
        refresh,
        "workspace_status",
        lambda _root: _status() | {"candidate": candidate | {"worktree_path": "/candidate"}},
    )
    monkeypatch.setattr(refresh, "changed_paths", lambda _path: ("dirty",))

    assert refresh.refresh_work_lane_base(root=tmp_path)["required_gaps"] == [gap]


def test_refresh_rejects_snapshot_drift_before_rebase(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _common(monkeypatch)
    monkeypatch.setattr(refresh, "is_ancestor", lambda *_args: False)
    monkeypatch.setattr(refresh, "current_tracked_head", lambda _root: "drift")

    report = refresh.refresh_work_lane_base(
        root=tmp_path, apply=True, authorized=True, expect_head=HEAD
    )

    assert report["required_gaps"] == ["refresh_base_snapshot_stale:work_lane"]


def test_refresh_conflict_reports_failed_restore(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _common(monkeypatch)
    monkeypatch.setattr(refresh, "is_ancestor", lambda *_args: False)
    monkeypatch.setattr(refresh, "current_tracked_head", lambda _root: HEAD)

    def run_git(_root: Path, *args: str, **_kwargs: object) -> SimpleNamespace:
        if "rebase" in args and "--abort" not in args:
            return _completed(returncode=1, stderr="CONFLICT (content): conflict")
        return _completed(stdout=(HEAD if args[-2:] == ("rev-parse", "HEAD") else CANDIDATE) + "\n")

    monkeypatch.setattr(refresh, "run_git", run_git)
    monkeypatch.setattr(
        refresh,
        "attach_worktree",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("attachment stale")),
    )

    report = refresh.refresh_work_lane_base(
        root=tmp_path, apply=True, authorized=True, expect_head=HEAD
    )

    assert report["required_gaps"] == [
        "refresh_base_failed",
        "refresh_base_worktree_restore_failed",
    ]
    assert "CONFLICT" in str(report["stderr"])


def test_refresh_rejects_rebase_postcondition_and_restores_branch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _common(monkeypatch)
    ancestry = iter((False, False))
    monkeypatch.setattr(refresh, "is_ancestor", lambda *_args: next(ancestry))
    heads = iter((HEAD, REBASED, HEAD))
    monkeypatch.setattr(refresh, "current_tracked_head", lambda _root: next(heads))
    attached: list[tuple[str, str]] = []
    monkeypatch.setattr(
        refresh,
        "attach_worktree",
        lambda _root, _path, *, branch, head: attached.append((branch, head)) or SimpleNamespace(),
    )

    report = refresh.refresh_work_lane_base(
        root=tmp_path, apply=True, authorized=True, expect_head=HEAD
    )

    assert report["required_gaps"] == ["refresh_base_postcondition_failed"]
    assert attached == [(BRANCH, HEAD)]


@pytest.mark.parametrize("case", ["ambiguous", "multiple", "wrong-branch", "recovered"])
def test_detached_public_recovery_accepts_only_exact_persisted_effect(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case: str,
) -> None:
    _common(monkeypatch, branch="detached")
    plan = {
        "ambiguous": None,
        "multiple": _recovery_plan(
            updates={
                f"refs/heads/{BRANCH}": GitRefUpdate(expected=HEAD, desired=REBASED),
                "refs/heads/work/other": GitRefUpdate(expected="d" * 40, desired="e" * 40),
            }
        ),
        "wrong-branch": _recovery_plan(
            updates={"refs/heads/dev": GitRefUpdate(expected=HEAD, desired=REBASED)},
            execution_branch="dev",
        ),
        "recovered": _recovery_plan(),
    }[case]
    monkeypatch.setattr(refresh, "current_tracked_head", lambda _root: REBASED)
    monkeypatch.setattr(refresh, "recover_plan", lambda *_args, **_kwargs: plan)
    attached: list[tuple[str, str]] = []
    monkeypatch.setattr(
        refresh,
        "attach_worktree",
        lambda _root, _path, *, branch, head: attached.append((branch, head)) or SimpleNamespace(),
    )

    def execute(_root: Path, _plan: object, **kwargs: object) -> SimpleNamespace:
        projection = cast("Callable[[], object]", kwargs["projection"])
        projection()
        return SimpleNamespace()

    monkeypatch.setattr(refresh, "execute_git_effect", execute)

    report = refresh.refresh_work_lane_base(root=tmp_path, apply=True)

    if case == "recovered":
        assert report["state"] == "base_refreshed"
        assert report["previous_head"] == HEAD
        assert attached == [(BRANCH, REBASED)]
    else:
        assert report["state"] == "blocked"
        assert report["required_gaps"] == [
            "git_effect_recovery_ambiguous"
            if case == "ambiguous"
            else "git_effect_recovery_unproven"
        ]


@pytest.mark.parametrize("case", ["ref-drift", "effect-fails"])
def test_refresh_public_effect_failure_restores_original_checkout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case: str,
) -> None:
    _common(monkeypatch)
    monkeypatch.setattr(refresh, "is_ancestor", lambda *_args: False)
    heads = iter((HEAD, REBASED, REBASED if case == "effect-fails" else HEAD, HEAD, HEAD))
    monkeypatch.setattr(refresh, "current_tracked_head", lambda _root: next(heads))
    _stub_refresh_effect(monkeypatch)
    monkeypatch.setattr(
        refresh, "ref_head", lambda *_args: "other" if case == "ref-drift" else REBASED
    )
    monkeypatch.setattr(
        refresh,
        "execute_git_effect",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("stale effect")),
    )
    restored: list[tuple[str, str]] = []
    monkeypatch.setattr(refresh, "compensate_git_worktree", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        refresh,
        "attach_worktree",
        lambda _root, _path, *, branch, head: restored.append((branch, head)) or SimpleNamespace(),
    )

    report = refresh.refresh_work_lane_base(
        root=tmp_path, apply=True, authorized=True, expect_head=HEAD
    )

    assert report["state"] == "blocked"
    assert restored == [(BRANCH, HEAD)]


def test_refresh_public_attachment_failure_is_reported(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _common(monkeypatch)
    ancestry = iter((False, True))
    monkeypatch.setattr(refresh, "is_ancestor", lambda *_args: next(ancestry))
    heads = iter((HEAD, REBASED, REBASED, REBASED, HEAD, HEAD))
    monkeypatch.setattr(refresh, "current_tracked_head", lambda _root: next(heads))
    _stub_refresh_effect(monkeypatch)
    monkeypatch.setattr(refresh, "ref_head", lambda *_args: "other")

    def execute(_root: Path, _plan: object, **kwargs: object) -> None:
        projection = cast("Callable[[], object]", kwargs["projection"])
        projection()

    monkeypatch.setattr(refresh, "execute_git_effect", execute)
    monkeypatch.setattr(
        refresh,
        "attach_worktree",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("branch occupied")),
    )
    monkeypatch.setattr(refresh, "compensate_git_worktree", lambda *_args, **_kwargs: None)

    report = refresh.refresh_work_lane_base(
        root=tmp_path, apply=True, authorized=True, expect_head=HEAD
    )

    assert report["required_gaps"] == [
        "refresh_base_worktree_attach_failed",
        "refresh_base_worktree_restore_failed",
    ]
    stderr = str(report["stderr"])
    assert "attachment" in stderr or "branch" in stderr
