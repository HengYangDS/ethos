from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.adapters.openspec.cli as openspec_cli
from ethos.adapters.admission.prewrite import prewrite_guard
from ethos.adapters.admission.transitions import work_lane_ref_transition_report
from ethos.adapters.openspec.governance import openspec_governance_report
from ethos.adapters.openspec.lifecycle.scope import path_matches_scope
from tests.support.contract_helpers import commit_fixture_file
from tests.support.contract_helpers import git
from tests.support.contract_helpers import start_adopted_work_lane

if TYPE_CHECKING:
    from pathlib import Path


def test_scope_glob_matches_archive_directory_descendants() -> None:
    assert path_matches_scope(
        "openspec/changes/archive/2026-08-05-fixture-change/tasks.md",
        "openspec/changes/archive/*-fixture-change/**",
    )


def test_governance_allows_lease_bound_post_archive_closeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _repo, _candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    completed_head = git(worktree, "rev-parse", "HEAD")
    _stage_archive(worktree)
    git(worktree, "commit", "-m", "archive fixture change")
    archived_head = git(worktree, "rev-parse", "HEAD")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    transition = work_lane_ref_transition_report(
        root=worktree,
        phase="committed",
        ref_name=f"refs/heads/{git(worktree, 'branch', '--show-current')}",
        old_value=completed_head,
        new_value=archived_head,
    )
    assert transition["state"] == "lease_ref_advanced"
    _stub_official_archive_state(monkeypatch)

    report = openspec_governance_report(worktree, lifecycle=True)

    assert report["verdict"] == "pass"
    assert report["required_gaps"] == []
    assert report["change"] == "fixture-change"
    assert report["lifecycle"]["scope_binding"]["state"] == "post_archive_closeout"


def test_governance_allows_post_archive_closeout_descendant(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _repo, _candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    completed_head = git(worktree, "rev-parse", "HEAD")
    _stage_archive(worktree)
    git(worktree, "commit", "-m", "archive fixture change")
    archived_head = git(worktree, "rev-parse", "HEAD")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    transition = work_lane_ref_transition_report(
        root=worktree,
        phase="committed",
        ref_name=f"refs/heads/{git(worktree, 'branch', '--show-current')}",
        old_value=completed_head,
        new_value=archived_head,
    )
    assert transition["state"] == "lease_ref_advanced"
    commit_fixture_file(
        worktree,
        "README.md",
        "# Fixture\n\nPost-archive closeout repair.\n",
        "repair post-archive closeout",
    )
    _stub_official_archive_state(monkeypatch)

    report = openspec_governance_report(worktree, lifecycle=True)

    assert report["verdict"] == "pass"
    assert report["required_gaps"] == []
    assert report["change"] == "fixture-change"
    assert report["lifecycle"]["scope_binding"]["state"] == "post_archive_closeout"


def test_governance_allows_current_lease_staged_completion_transition(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _repo, _candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    tasks = worktree / "openspec" / "changes" / "fixture-change" / "tasks.md"
    tasks.write_text("- [x] Exercise fixture lifecycle\n", encoding="utf-8")
    git(worktree, "add", tasks.relative_to(worktree).as_posix())
    _stub_official_archive_state(monkeypatch, completed=True)

    report = openspec_governance_report(
        worktree,
        lifecycle=True,
        changed_paths=(tasks.relative_to(worktree).as_posix(),),
        require_workspace=False,
    )

    assert report["verdict"] == "pass"
    assert report["required_gaps"] == []
    assert report["change"] == "fixture-change"
    assert report["lifecycle"]["scope_binding"]["state"] == "completion_transition"
    prewrite = prewrite_guard(
        root=worktree,
        paths=[tasks],
        editor_root=worktree,
        require_editor_root=True,
    )
    assert prewrite["verdict"] == "pass", prewrite
    assert prewrite["required_gaps"] == []


@pytest.mark.parametrize("extra_path", ["README.md", "tests/extra.py"])
def test_governance_rejects_completion_transition_with_extra_mutation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, extra_path: str
) -> None:
    _repo, _candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    tasks = worktree / "openspec" / "changes" / "fixture-change" / "tasks.md"
    tasks.write_text("- [x] Exercise fixture lifecycle\n", encoding="utf-8")
    extra = worktree / extra_path
    extra.parent.mkdir(parents=True, exist_ok=True)
    extra.write_text("extra mutation\n", encoding="utf-8")
    git(worktree, "add", tasks.relative_to(worktree).as_posix(), extra_path)
    _stub_official_archive_state(monkeypatch, completed=True)

    report = openspec_governance_report(
        worktree,
        lifecycle=True,
        changed_paths=(tasks.relative_to(worktree).as_posix(), extra_path),
        require_workspace=False,
    )

    assert report["verdict"] == "block"
    assert "openspec_active_change_missing" in report["required_gaps"]


def test_governance_allows_current_lease_staged_archive_transition(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _repo, _candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    changed_paths = _stage_archive(worktree)
    _stub_official_archive_state(monkeypatch)

    report = openspec_governance_report(
        worktree,
        lifecycle=True,
        changed_paths=changed_paths,
        require_workspace=False,
    )

    assert report["verdict"] == "pass"
    assert report["required_gaps"] == []
    assert report["change"] == "fixture-change"
    assert report["lifecycle"]["scope_binding"]["state"] == "archive_transition"
    prewrite = prewrite_guard(
        root=worktree,
        paths=[worktree / path for path in changed_paths],
        editor_root=worktree,
        require_editor_root=True,
    )
    assert prewrite["verdict"] == "pass", prewrite
    assert prewrite["required_gaps"] == []


@pytest.mark.parametrize(
    "defect",
    ["missing_lease", "stale_head", "wrong_identity", "incomplete_tasks", "digest_drift"],
)
def test_governance_rejects_unbound_archive_transition(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, defect: str
) -> None:
    _repo, _candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    _stage_archive(
        worktree,
        archive_change="other-change" if defect == "wrong_identity" else "fixture-change",
        complete=defect != "incomplete_tasks",
        drift=defect == "digest_drift",
    )
    if defect == "stale_head":
        git(worktree, "commit", "-m", "archive without Lease advance")
    elif defect == "missing_lease":
        monkeypatch.setattr(
            "ethos.adapters.openspec.lifecycle.archive_transition.leases_by_branch",
            lambda _root: {},
        )
    _stub_official_archive_state(monkeypatch)

    report = openspec_governance_report(worktree, lifecycle=True)

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["openspec_active_change_missing"]


def _stage_archive(
    worktree: Path,
    *,
    archive_change: str = "fixture-change",
    complete: bool = True,
    drift: bool = False,
) -> tuple[str, ...]:
    active = worktree / "openspec" / "changes" / "fixture-change"
    archive = worktree / "openspec" / "changes" / "archive" / f"2026-08-04-{archive_change}"
    archive.parent.mkdir(parents=True)
    active.rename(archive)
    (archive / "tasks.md").write_text(
        f"- [{'x' if complete else ' '}] Exercise fixture lifecycle\n",
        encoding="utf-8",
    )
    if drift:
        commitment = archive / "commitment.toml"
        commitment.write_text(
            commitment.read_text(encoding="utf-8").replace(
                "Exercise the governed fixture lifecycle.",
                "Drift from the Lease-bound intent.",
            ),
            encoding="utf-8",
        )
    git(worktree, "add", ".")
    return tuple(
        git(worktree, "diff", "--cached", "--name-only", "--diff-filter=ACMRTD").splitlines()
    )


def _stub_official_archive_state(
    monkeypatch: pytest.MonkeyPatch, *, completed: bool = False
) -> None:
    monkeypatch.setattr(openspec_cli, "openspec_base_command", lambda: ("openspec",))

    def run_json(_root: Path, _base: tuple[str, ...], args: tuple[str, ...]):
        payload = (
            {"root": {"healthy": True}}
            if args[0] == "doctor"
            else {
                "changes": [
                    {
                        "name": "fixture-change",
                        "completedTasks": 1,
                        "totalTasks": 1,
                        "status": "complete",
                    }
                ]
                if completed
                else []
            }
            if args[0] == "list"
            else {"items": [], "summary": {}}
        )
        return {
            "command": [*_base, *args],
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "json": payload,
            "parse_error": "",
        }

    monkeypatch.setattr(openspec_cli, "run_json", run_json)
