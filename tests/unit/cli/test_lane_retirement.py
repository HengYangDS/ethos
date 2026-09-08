from __future__ import annotations

import json
import shlex
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path

import pytest

import ethos.adapters.repo.git_effects as git_effects
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.lease.projection import observe_lease
from ethos.adapters.store.state.schema import state_database
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import exact_lease
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_test_profile
from tests.support.runtime_scenarios import install_fixture_hook_runtime


@pytest.mark.parametrize(
    ("command", "options"),
    [
        (("superseded",), ("--path",)),
        ((), ("abandon", "recover")),
    ],
)
def test_retirement_help_exposes_recovery_inputs(command, options):
    completed = run_ethos_raw("lane", "retire", *command, "--help")
    assert completed.returncode == 0, completed.stderr
    assert all(option in completed.stdout for option in options)


@pytest.mark.parametrize(
    "boundary", ["current", "pre_adoption", "dirty", "foreign_lease", "stale_head", "locked"]
)
def test_landed_topic_retirement_obeys_the_exact_resource_boundary(
    tmp_path: Path, boundary: str
) -> None:
    """The public command retires only exact, clean, admitted topic resources."""
    repo = init_git_repo(tmp_path / "repo")
    historical = git(repo, "rev-parse", "HEAD")
    adopt_and_commit(repo)
    accepted = git(repo, "rev-parse", "HEAD")
    source = historical if boundary == "pre_adoption" else accepted
    branch = "topic/absorbed"
    worktree = tmp_path / "absorbed"
    git(repo, "worktree", "add", "-b", branch, worktree.as_posix(), source)
    if boundary == "dirty":
        (worktree / "unique.txt").write_text("unabsorbed work\n", encoding="utf-8")
    elif boundary == "foreign_lease":
        acquire_lease(
            state_database(repo),
            lease=exact_lease(branch=branch, holder_ref="agent:test:case:other"),
        )
    elif boundary == "locked":
        git(repo, "worktree", "lock", worktree.as_posix())
    install_fixture_hook_runtime(repo)

    args = (
        "lane",
        "retire",
        "landed",
        "--branch",
        branch,
        "--expect-head",
        "0" * 40 if boundary == "stale_head" else source,
        "--root",
        repo.as_posix(),
        "--authorize",
        "--json",
    )
    if boundary in {"current", "pre_adoption"}:
        planned = run_ethos(*args, cwd=repo)
        assert (planned["verdict"], planned["required_gaps"]) == ("pass", [])
        assert run_ethos(*args, "--apply", cwd=repo)["verdict"] == "pass"
        assert not worktree.exists()
        assert git(repo, "branch", "--list", branch) == ""
        assert git(repo, "rev-parse", "dev") == accepted
        assert observe_lease(state_database(repo), branch).state == "missing"
        return
    blocked = run_ethos_blocked(*args, "--apply", cwd=repo)
    expected = {
        "dirty": "work_lane_dirty",
        "foreign_lease": "foreign_work_lane_retire_authority_required",
        "stale_head": "expect_head_mismatch",
    }
    if boundary in expected:
        assert expected[boundary] in blocked["required_gaps"]
    assert worktree.is_dir()
    assert git(repo, "rev-parse", branch) == source
    if boundary == "dirty":
        assert (worktree / "unique.txt").read_text(encoding="utf-8") == "unabsorbed work\n"
    if boundary == "foreign_lease":
        assert observe_lease(state_database(repo), branch).state == "valid"


@pytest.mark.parametrize(
    "boundary",
    [
        "retained",
        "moved",
        "cas_race",
        "owned",
        "expired",
        "dirty",
        "foreign_lease",
        "missing",
        "unrelated",
        "self",
        "protected",
        "candidate",
        "stale_head",
        "symbolic",
        "missing_actor",
        "direct_apply",
        "wrong_root",
        "foreign_identity",
    ],
)
def test_retained_topic_retirement_binds_the_surviving_ref(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, boundary: str
) -> None:
    """Retiring a duplicate preserves history and refuses stale retention evidence."""
    repo, worktree, source, accepted, survivor, selected = _retained_topic_case(
        tmp_path, monkeypatch, boundary
    )
    branch, retained = "codex/duplicate", "refs/heads/codex/survivor"
    args = (
        "lane",
        "retire",
        "superseded",
        "--branch",
        branch,
        "--expect-head",
        "0" * 40 if boundary == "stale_head" else source,
        "--absorbed-by",
        selected,
        "--reason",
        "duplicate history retained",
        "--root",
        str(worktree if boundary == "wrong_root" else repo),
        "--json",
    )
    if boundary == "direct_apply":
        args += ("--apply", "--authorize")
    planned = (run_ethos_blocked if boundary == "direct_apply" else run_ethos)(*args, cwd=repo)
    expected = {
        "dirty": "work_lane_dirty",
        "foreign_lease": "foreign_work_lane_retire_authority_required",
        "missing": "retained_ref_missing",
        "unrelated": "retained_ref_does_not_contain_target",
        "self": "retained_ref_is_target",
        "protected": "retained_ref_not_topic",
        "candidate": "retained_ref_not_topic",
        "stale_head": "expect_head_mismatch",
        "symbolic": "retained_ref_symbolic",
        "missing_actor": f"invocation_actor_missing:{branch}",
        "direct_apply": "lane_retirement_receipt_required",
        "wrong_root": "retirement_requires_accepted_control_root",
        "foreign_identity": "git_effect_repository_identity_mismatch",
    }
    if boundary in expected:
        assert expected[boundary] in planned["required_gaps"]
        assert (
            worktree.is_dir(),
            git(repo, "rev-parse", branch),
            git(repo, "rev-parse", "dev"),
        ) == (True, source, accepted)
        return
    assert (planned["verdict"], planned["required_gaps"]) == ("pass", [])
    operation = json.loads(Path(planned["data"]["receipt"]["path"]).read_text())
    assert operation["git_plan"]["commitment"] is None
    assert operation["git_plan"]["facts"]["values"]["assertions"][retained] == survivor
    if boundary == "moved":
        git(repo, "update-ref", retained, accepted, survivor)
    if boundary == "cas_race":
        execute = git_effects.run_git

        def move_before_cas(*args, **kwargs):
            if args[1:3] == ("update-ref", "--stdin"):
                git(repo, "update-ref", retained, accepted, survivor)
            return execute(*args, **kwargs)

        monkeypatch.setattr(git_effects, "run_git", move_before_cas)
    command = shlex.split(planned["next_action"])[1:]
    result = (run_ethos_blocked if boundary in {"moved", "cas_race"} else run_ethos)(
        *command, cwd=repo
    )
    assert git(repo, "rev-parse", "dev") == accepted
    assert git(repo, "rev-parse", retained) == (
        accepted if boundary in {"moved", "cas_race"} else survivor
    )
    if boundary in {"moved", "cas_race"}:
        assert (
            "git_effect_cas_rejected" if boundary == "cas_race" else "git_effect_cas_mismatch"
        ) in result["required_gaps"]
        assert (worktree.is_dir(), git(repo, "rev-parse", branch)) == (boundary == "moved", source)
    else:
        assert result["state"] == "retired"
        assert (worktree.exists(), git(repo, "branch", "--list", branch)) == (False, "")
        assert git(repo, "show", f"{retained}:unique.txt") == "historical semantics"
        assert observe_lease(state_database(repo), branch).state == "missing"


def _retained_topic_case(tmp_path, monkeypatch, boundary):
    """Construct retained history and one independently varied admission boundary."""
    repo = init_git_repo(tmp_path / "repo")
    branch, retained = "codex/duplicate", "refs/heads/codex/survivor"
    worktree = tmp_path / "duplicate"
    git(repo, "worktree", "add", "-b", branch, str(worktree))
    (worktree / "unique.txt").write_text("historical semantics\n", encoding="utf-8")
    source = commit_fixture(worktree, "historical work")
    if boundary == "foreign_identity":
        adopt_and_commit(worktree)
        write_test_profile(worktree, profile_id="foreign")
        source = commit_fixture(worktree, "foreign identity")
    survivor = git(
        repo,
        "commit-tree",
        git(worktree, "rev-parse", "HEAD^{tree}"),
        "-p",
        source,
        "-m",
        "retain historical work",
    )
    git(repo, "update-ref", retained, survivor)
    adopt_and_commit(repo)
    accepted = git(repo, "rev-parse", "HEAD")
    install_fixture_hook_runtime(repo)
    if boundary in {"owned", "expired", "foreign_lease"}:
        lease = exact_lease(
            branch=branch,
            holder_ref=(
                "agent:test:case:agent-test" if boundary == "owned" else "agent:test:case:other"
            ),
        )
        if boundary == "expired":
            lease = lease.model_copy(update={"expires_at": datetime.now(UTC) - timedelta(days=1)})
        acquire_lease(state_database(repo), lease=lease)
    if boundary == "dirty":
        (worktree / "pending.txt").write_text("preserve overlay", encoding="utf-8")
    if boundary == "missing_actor":
        monkeypatch.delenv("ETHOS_ACTOR", raising=False)
    selected = {
        "missing": "refs/heads/missing",
        "self": f"refs/heads/{branch}",
        "protected": "refs/heads/dev",
        "candidate": "refs/heads/candidate/dev",
    }.get(boundary, retained)
    if boundary == "unrelated":
        git(repo, "update-ref", retained, accepted, survivor)
    if boundary == "symbolic":
        selected = "refs/heads/alias"
        git(repo, "symbolic-ref", selected, retained)
    return repo, worktree, source, accepted, survivor, selected
