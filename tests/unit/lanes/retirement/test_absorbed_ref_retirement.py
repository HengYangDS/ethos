from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING
from typing import cast

import ethos.adapters.mutation.lane_retirement.absorbed as absorbed_retirement
from ethos.adapters.admission.ref_intent import write_ref_intent
from ethos.adapters.repo.hook_runtime import install_hook_launchers
from ethos.adapters.store.state.lease.projection import observe_lease
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.plan import GitRefUpdate
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Mapping
    from pathlib import Path

    import pytest

    from ethos.contracts.plan import TransitionPlan
    from ethos.contracts.semantic import Attestation


def _absorbed_ref(tmp_path: Path) -> tuple[Path, str, str]:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    source = git(repo, "rev-parse", "HEAD")
    git(repo, "branch", "work/absorbed", source)
    marker = repo / "accepted.txt"
    marker.write_text("accepted\n", encoding="utf-8")
    git(repo, "add", marker.name)
    git(
        repo,
        "commit",
        "-m",
        "advance accepted truth",
    )
    return repo, source, git(repo, "rev-parse", "HEAD")


def _retire(
    repo: Path,
    *,
    branch: str,
    source: str,
    accepted: str,
    apply: bool = True,
    blocked: bool = False,
) -> dict[str, object]:
    command = run_ethos_blocked if blocked else run_ethos
    arguments = (
        "lane",
        "retire",
        "absorbed-ref",
        "--branch",
        branch,
        "--expect-head",
        source,
        "--accepted-head",
        accepted,
        "--root",
        repo.as_posix(),
        "--authorize",
        "--confirm-irreversible",
        *(("--apply",) if apply else ()),
        "--json",
    )
    return command(*arguments, cwd=repo)


def _raw_delete(repo: Path, branch: str, source: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ("git", "update-ref", "-d", f"refs/heads/{branch}", source),
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )


def test_absorbed_ref_retires_exact_unbound_unleased_ancestor(tmp_path: Path) -> None:
    repo, source, accepted = _absorbed_ref(tmp_path)
    planned = _retire(repo, branch="work/absorbed", source=source, accepted=accepted, apply=False)
    assert (planned["verdict"], planned["state"], planned["required_gaps"]) == (
        "pass",
        "ready_to_retire_absorbed_ref",
        [],
    )
    applied = _retire(repo, branch="work/absorbed", source=source, accepted=accepted)

    assert (applied["verdict"], applied["state"], applied["required_gaps"]) == (
        "pass",
        "retired_absorbed_ref",
        [],
    )
    receipt = applied["data"]["retired"]
    assert receipt == {
        "branch": "work/absorbed",
        "head": source,
        "accepted_head": accepted,
        "ref_state": "absent",
        "worktree_binding": "absent",
        "lease_state": "missing",
    }
    assert git(repo, "branch", "--list", "work/absorbed") == ""
    assert observe_lease(state_database(repo), "work/absorbed").state == "missing"


def test_absorbed_ref_retires_through_installed_reference_transaction_hook(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, source, accepted = _absorbed_ref(tmp_path)
    protected_before = {
        branch: git(repo, "rev-parse", branch)
        for branch in ("dev", "main", "candidate/dev")
        if git(repo, "branch", "--list", branch)
    }
    install_hook_launchers(repo)
    execute = absorbed_retirement.execute_git_effect
    observed_policy: dict[str, object] = {}

    def capture_policy(
        root: Path,
        plan: TransitionPlan,
        *,
        issuer: str,
        environment: Mapping[str, str] | None = None,
        projection: Callable[[], None] | None = None,
        detached_branch: str = "",
    ) -> Attestation:
        observed_policy.update(plan.policy)
        return execute(
            root,
            plan,
            issuer=issuer,
            environment=environment,
            projection=projection,
            detached_branch=detached_branch,
        )

    monkeypatch.setattr(absorbed_retirement, "execute_git_effect", capture_policy)

    applied = _retire(
        repo,
        branch="work/absorbed",
        source=source,
        accepted=accepted,
    )

    assert (applied["verdict"], applied["state"], applied["required_gaps"]) == (
        "pass",
        "retired_absorbed_ref",
        [],
    )
    assert applied["data"]["retired"]["ref_state"] == "absent"
    assert git(repo, "branch", "--list", "work/absorbed") == ""
    assert observed_policy["operation"] == "lane.retire"
    assert observed_policy["retirement_kind"] == "absorbed-ref"
    assert {
        branch: git(repo, "rev-parse", branch) for branch in protected_before
    } == protected_before

    git(repo, "branch", "work/wrong-operation", source)
    update = GitRefUpdate(expected=source, desired="0" * len(source))
    write_ref_intent(
        root=repo,
        ref_name="refs/heads/work/wrong-operation",
        update=update,
        operation="lane.retire.absorbed-ref",
        plan_digest="0" * 64,
    )
    wrong_operation = _raw_delete(repo, "work/wrong-operation", source)

    assert wrong_operation.returncode != 0
    assert git(repo, "rev-parse", "work/wrong-operation") == source


def test_absorbed_ref_retires_legacy_source_without_branch_policy_through_current_policy(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    source = git(repo, "rev-parse", "HEAD")
    adopt_and_commit(repo)
    missing_policy = subprocess.run(
        ("git", "show", f"{source}:.ethos/workspace.toml"),
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    assert missing_policy.returncode != 0
    adopt_and_commit(repo)
    accepted = git(repo, "rev-parse", "HEAD")
    git(repo, "branch", "work/legacy-absorbed", source)
    install_hook_launchers(repo)

    applied = _retire(
        repo,
        branch="work/legacy-absorbed",
        source=source,
        accepted=accepted,
    )

    assert (applied["verdict"], applied["state"], applied["required_gaps"]) == (
        "pass",
        "retired_absorbed_ref",
        [],
    )
    assert git(repo, "branch", "--list", "work/legacy-absorbed") == ""


def test_legacy_absorbed_ref_deletion_without_exact_retirement_intent_is_blocked(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    source = git(repo, "rev-parse", "HEAD")
    adopt_and_commit(repo)
    git(repo, "branch", "work/legacy-unintended", source)
    install_hook_launchers(repo)

    deleted = _raw_delete(repo, "work/legacy-unintended", source)

    assert deleted.returncode != 0
    assert git(repo, "rev-parse", "work/legacy-unintended") == source


def test_installed_hook_retires_two_legacy_refs_under_exact_legacy_accepted_policy(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    source = git(repo, "rev-parse", "HEAD")
    adopt_and_commit(repo)
    legacy_policy = """[branch_roles]
release_branch = "main"
accepted_branch = "dev"
candidate_branch = "candidate/dev"
release_mirror = "accepted_ff"
work_branch_prefix = "work/"
proposal_branch_prefix = "proposal/"
repository_family_worktrees = true
"""
    workspace = repo / ".ethos/workspace.toml"
    workspace.write_text(legacy_policy, encoding="utf-8")
    git(repo, "add", workspace.relative_to(repo).as_posix())
    git(repo, "commit", "-m", "adopt legacy branch-role policy")
    accepted = git(repo, "rev-parse", "HEAD")
    branches = ("work/legacy-one", "work/legacy-two")
    for branch in branches:
        git(repo, "branch", branch, source)
    install_hook_launchers(repo)

    raw = _raw_delete(repo, branches[0], source)
    assert raw.returncode != 0

    for branch in branches:
        applied = _retire(repo, branch=branch, source=source, accepted=accepted)
        assert (applied["verdict"], applied["state"]) == (
            "pass",
            "retired_absorbed_ref",
        )

    assert git(repo, "branch", "--list", "work/*") == ""


def test_absorbed_ref_fails_closed_when_ref_is_not_an_accepted_ancestor(tmp_path: Path) -> None:
    repo, source, accepted = _absorbed_ref(tmp_path)
    git(repo, "branch", "-f", "work/absorbed", accepted)
    changed = git(repo, "rev-parse", "work/absorbed")

    payload = _retire(
        repo,
        branch="work/absorbed",
        source=changed,
        accepted=source,
        blocked=True,
    )

    assert "accepted_head_mismatch" in payload["required_gaps"]
    assert git(repo, "rev-parse", "work/absorbed") == changed


def test_absorbed_ref_reobserves_before_delete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, source, accepted = _absorbed_ref(tmp_path)
    original = absorbed_retirement.workspace_status
    calls = 0

    def worktree_appeared(root: Path) -> dict[str, object]:
        nonlocal calls
        calls += 1
        status = original(root)
        if calls == 2:
            worktrees = cast("list[dict[str, object]]", status["worktrees"])
            status["worktrees"] = [
                *worktrees,
                {"branch": "work/absorbed", "path": "/appeared"},
            ]
        return status

    monkeypatch.setattr(absorbed_retirement, "workspace_status", worktree_appeared)
    payload = _retire(
        repo,
        branch="work/absorbed",
        source=source,
        accepted=accepted,
        blocked=True,
    )

    assert payload["required_gaps"] == ["absorbed_ref_worktree_appeared"]
    assert git(repo, "rev-parse", "work/absorbed") == source
