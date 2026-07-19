from __future__ import annotations

# fmt: off
import subprocess
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.admission.prewrite as prewrite
import ethos.adapters.mutation.lane_lifecycle.refresh as lane_refresh
from ethos.adapters.admission.prewrite import prewrite_guard
from ethos.adapters.mutation.lane_lifecycle.refresh import refresh_work_lane_base
from ethos.adapters.mutation.lanes import bind_work_lane_claim
from ethos.adapters.mutation.lanes import start_work_lane
from ethos.adapters.repo.runtime.core import runtime_binding
from ethos.adapters.repo.status.core import workspace_status
from ethos.adapters.store.state.lease.projection import active_leases
from ethos_core.contracts.branch.roles import BranchRolePolicy
from tests.support.contract_helpers import commit_fixture_file
from tests.support.contract_helpers import write_role_policy
from tests.support.lane_helpers import add_candidate_worktree
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo

if TYPE_CHECKING:
    from pathlib import Path


def test_branch_role_policy_semantic_order_uses_configured_roles_without_hardcoded_names() -> None:
    policy = BranchRolePolicy(
        release_branch="release",
        accepted_branch="integration",
        candidate_branch="stage/integration",
        work_branch_prefix="lane/",
        submit_branch_prefix="review/",
    )

    status = policy.as_status_policy()
    assert tuple(status[key] for key in status if key != "semantic_order") == (
        "release",
        "integration",
        "stage/integration",
        "lane/",
        "review/",
        "independent",
    )
    assert [
        (item["role"], item["kind"], item["config_key"], item["pattern"])
        for item in status["semantic_order"]
    ] == [
        ("release_root", "exact_branch", "release_branch", "release"),
        ("accepted_root", "exact_branch", "accepted_branch", "integration"),
        ("candidate", "exact_branch", "candidate_branch", "stage/integration"),
        ("work_lane", "branch_prefix", "work_branch_prefix", "lane/*"),
        ("submit_lane", "branch_prefix", "submit_branch_prefix", "review/*"),
    ]
    assert [policy.role_for_branch(branch) for branch in (
        "release", "integration", "stage/integration", "lane/feature", "review/feature",
        "main", "dev", "candidate/dev", "work/feature", "submit/feature",
    )] == [
        "release_root", "accepted_root", "candidate", "work_lane", "submit_lane",
        "other", "other", "other", "other", "other",
    ]


def test_start_work_lane_uses_configured_candidate_and_work_role_policy(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    write_role_policy(repo)
    git(
        repo,
        "worktree",
        "add",
        "-b",
        "stage/dev",
        (tmp_path / "repo-stage-dev").as_posix(),
        "dev",
    )
    worktree = tmp_path / "repo-lane-feature"

    report = start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        holder_ref="agent:test:case:agent-test",
        apply=True,
    )

    assert report["ok"] is True
    assert report["branch"] == "lane/feature"
    assert report["base"] == "stage/dev"
    assert git(worktree, "branch", "--show-current") == "lane/feature"


def test_existing_work_lane_claim_binding_can_be_applied_without_restarting_lane(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        holder_ref="agent:test:case:agent-test",
        apply=True,
    )

    report = bind_work_lane_claim(
        root=worktree,
        claim_id="sample-trust",
        apply=True,
    )
    status = workspace_status(worktree)

    assert report["ok"] is True
    assert report["state"] == "bound"
    assert report["branch"] == "work/feature"
    assert report["holder_ref"] == "agent:test:case:agent-test"
    assert report["claim_id"] == "sample-trust"
    closeout = status["closeout_support"]
    assert tuple(closeout[key] for key in (
        "supported", "branch", "target_branch", "operation", "holder_ref", "lease_epoch",
        "claim_id", "claim_binding", "required_gaps",
    )) == (True, "work/feature", "candidate/dev", "land_to_candidate", "agent:test:case:agent-test", 1, "sample-trust", "bound", [])
    assert closeout["target_path"] == candidate.as_posix()
    assert closeout["lease_id"]


def test_prewrite_rejects_tracked_path_from_accepted_root(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")

    report = prewrite_guard(
        root=repo,
        paths=[repo / "README.md"],
        editor_root=repo,
        require_editor_root=True,
    )

    assert report["ok"] is False
    assert report["error"] == "protected_lane_prewrite_blocked"
    assert report["role"] == "accepted_root"


def test_prewrite_allows_owned_work_lane_with_matching_editor_root(
    tmp_path: Path, monkeypatch
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-owned"
    start_work_lane(
        root=repo,
        name="owned",
        path=worktree,
        holder_ref="agent:test:case:agent-test",
        apply=True,
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")

    monkeypatch.setattr(prewrite, "workspace_status", pytest.fail, raising=False)

    report = prewrite.prewrite_guard(
        root=worktree,
        paths=[worktree / "README.md"],
        editor_root=worktree,
        require_editor_root=True,
    )

    assert (report["ok"], report["role"], report["error"]) == (True, "work_lane", "")


def test_prewrite_blocks_product_root_when_runner_source_differs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = init_repo(tmp_path / "repo")
    worktree = tmp_path / "repo-work-owned"
    git(repo, "worktree", "add", "-b", "work/owned", worktree.as_posix(), "dev")
    product_marker = worktree / "packages" / "ethos" / "src" / "ethos" / "__init__.py"
    product_marker.parent.mkdir(parents=True)
    product_marker.write_text("", encoding="utf-8")
    external_runner = tmp_path / "external" / "packages" / "ethos" / "src" / "ethos" / "__init__.py"
    external_runner.parent.mkdir(parents=True)
    (tmp_path / "external" / "pyproject.toml").write_text(
        "[project]\nname='external'\n", encoding="utf-8"
    )
    external_runner.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        "ethos.adapters.repo.runtime.core.ethos.__file__", external_runner.as_posix()
    )

    report = prewrite_guard(
        root=worktree,
        paths=[worktree / "README.md"],
        editor_root=worktree,
        require_editor_root=True,
    )

    assert report["ok"] is False
    assert report["error"] == "root_binding_mismatch"
    assert report["runtime_binding"]["product_audit_root"] is True
    assert report["runtime_binding"]["runner_matches_audit_root"] is False


def test_prewrite_rejects_work_lane_without_editor_root_binding(
    tmp_path: Path, monkeypatch
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-owned"
    start_work_lane(
        root=repo,
        name="owned",
        path=worktree,
        holder_ref="agent:test:case:agent-test",
        apply=True,
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")

    report = prewrite_guard(
        root=worktree,
        paths=[worktree / "README.md"],
    )

    assert report["ok"] is False
    assert report["role"] == "work_lane"
    assert report["error"] == "editor_root_missing"


def test_prewrite_rejects_protected_lane_roles(tmp_path: Path) -> None:
    cases = {
        "release_root": ("main",),
        "candidate": ("candidate/dev",),
        "submit_lane": ("submit/review",),
        "other": ("feature/unknown",),
    }
    for role, checkout_args in cases.items():
        repo = init_repo(tmp_path / f"repo-{role}")
        git(repo, "checkout", "-b", *checkout_args)

        report = prewrite_guard(
            root=repo,
            paths=[repo / "README.md"],
            editor_root=repo,
            require_editor_root=True,
        )

        assert report["ok"] is False
        assert report["role"] == role
        assert report["error"] == "protected_lane_prewrite_blocked"


def test_prewrite_rejects_detached_lane(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo-detached")
    git(repo, "checkout", "--detach", "HEAD")

    report = prewrite_guard(
        root=repo,
        paths=[repo / "README.md"],
        editor_root=repo,
        require_editor_root=True,
    )

    assert report["ok"] is False
    assert report["role"] == "detached"
    assert report["error"] == "protected_lane_prewrite_blocked"


def test_start_work_lane_apply_creates_worktree_and_records_lease(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"

    report = start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        holder_ref="agent:test:case:agent-test",
        apply=True,
    )

    assert report["ok"] is True
    assert report["branch"] == "work/feature"
    assert report["worktree"] == {
        "branch": "work/feature",
        "path": worktree.resolve().as_posix(),
        "head": git(worktree, "rev-parse", "HEAD"),
        "role": "work_lane",
        "worktree_binding": "linked",
    }
    assert worktree.exists()
    assert git(worktree, "branch", "--show-current") == "work/feature"
    leases = active_leases(repo / ".ethos" / "state" / "state.sqlite")
    assert [(lease["subject"], lease["holder_ref"]) for lease in leases] == [
        ("work/feature", "agent:test:case:agent-test")
    ]


def test_start_work_lane_defaults_path_to_sibling_candidate_home(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    expected = repo.with_name(f"{repo.name}-work-feature")

    report = start_work_lane(
        root=repo,
        name="feature",
        holder_ref="agent:test:case:agent-test",
        apply=True,
    )

    assert report["ok"] is True
    assert report["path"] == expected.resolve().as_posix()
    assert expected.exists()
    assert git(expected, "branch", "--show-current") == "work/feature"


@pytest.mark.parametrize(
    ("mode", "expected_gap"),
    [
        ("branch_missing", "candidate_branch_missing"),
        ("worktree_missing", "candidate_worktree_missing"),
        ("worktree_dirty", "candidate_worktree_dirty"),
    ],
)
def test_start_work_lane_apply_requires_ready_candidate(
    tmp_path: Path, mode: str, expected_gap: str
) -> None:
    repo = init_repo(tmp_path / "repo")
    if mode == "worktree_missing":
        git(repo, "branch", "candidate/dev", "dev")
    elif mode == "worktree_dirty":
        candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
        (candidate / "README.md").write_text("# dirty candidate\n", encoding="utf-8")
    worktree = tmp_path / "repo-work-feature"
    report = start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        holder_ref="agent:test:case:agent-test",
        apply=True,
    )
    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert expected_gap in report["required_gaps"]
    assert not worktree.exists()


def test_start_work_lane_apply_starts_from_candidate_branch(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    candidate_head = git(repo, "rev-parse", "candidate/dev")
    (repo / "README.md").write_text("# changed on dev\n", encoding="utf-8")
    commit_fixture_file(repo, "README.md", "# changed on dev\n", "advance dev only")
    worktree = tmp_path / "repo-work-feature"

    report = start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        holder_ref="agent:test:case:agent-test",
        apply=True,
    )

    assert report["ok"] is True
    assert git(worktree, "rev-parse", "HEAD") == candidate_head
    assert git(repo, "rev-parse", "dev") != candidate_head



def _stale_work_lane(
    tmp_path: Path,
    *,
    candidate_path: str = "CANDIDATE.md",
    lane_path: str = "FEATURE.md",
    commit_lane: bool = True,
) -> tuple[Path, Path, Path, str, str]:
    repo = init_repo(tmp_path / "repo")
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    git(repo, "worktree", "add", "-b", "work/feature", worktree.as_posix(), "candidate/dev")
    commit_fixture_file(candidate, candidate_path, "# candidate\n", "advance candidate")
    if commit_lane:
        commit_fixture_file(worktree, lane_path, "# feature\n", "feature work")
    return repo, candidate, worktree, git(worktree, "rev-parse", "HEAD"), git(
        candidate, "rev-parse", "HEAD"
    )


def _rules(root: Path, records: list[tuple[str, int]]) -> None:
    blocks = [
        "\n".join(
            (
                "[[quality.source_budget.debt.records]]",
                f'id = "{identifier}"',
                'owner = "test"',
                'replacement = "test replacement"',
                'deletion_wave = "test"',
                'expiry = "test"',
                f"allowance = {allowance}",
            )
        )
        for identifier, allowance in records
    ]
    rules = root / ".ethos" / "rules.toml"
    rules.parent.mkdir(exist_ok=True)
    rules.write_text(
        "\n\n".join(
            (
                "[quality.source_budget.debt]",
                f"maximum_total = {sum(allowance for _identifier, allowance in records)}",
                *blocks,
                '[gates.local-state-audit]\ncommand = "test"\nblocking = true',
                "",
            )
        ),
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    ("candidate_record", "lane_record", "outside_change", "ok"),
    [
        ("candidate", "lane", False, True),
        ("shared", "shared", False, False),
        ("candidate", "lane", True, False),
    ],
)
def test_refresh_work_lane_base_handles_source_budget_debt_conflicts(
    tmp_path: Path, candidate_record: str, lane_record: str, *, outside_change: bool, ok: bool
) -> None:
    repo = init_repo(tmp_path / "repo")
    _rules(repo, [("base", 10)])
    rules = ".ethos/rules.toml"
    commit_fixture_file(repo, rules, (repo / rules).read_text(encoding="utf-8"), "declare source budget debt")
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    git(repo, "worktree", "add", "-b", "work/feature", worktree.as_posix(), "candidate/dev")
    _rules(candidate, [("base", 10), (candidate_record, 20)])
    if outside_change:
        candidate_rules = candidate / rules
        candidate_rules.write_text(
            candidate_rules.read_text(encoding="utf-8") + "\n[unrelated]\nvalue = true\n",
            encoding="utf-8",
        )
    commit_fixture_file(
        candidate,
        rules,
        (candidate / rules).read_text(encoding="utf-8"),
        "add candidate debt",
    )
    _rules(worktree, [("base", 10), (lane_record, 30)])
    commit_fixture_file(
        worktree,
        rules,
        (worktree / rules).read_text(encoding="utf-8"),
        "add lane debt",
    )
    previous_head = git(worktree, "rev-parse", "HEAD")
    candidate_head = git(candidate, "rev-parse", "HEAD")

    report = refresh_work_lane_base(
        root=worktree, apply=True, authorized=True, expect_head=previous_head
    )

    assert report["ok"] is ok
    if not ok:
        assert report["required_gaps"] == ["refresh_base_failed"]
        assert git(worktree, "rev-parse", "HEAD") == previous_head
        return
    merged = (worktree / ".ethos" / "rules.toml").read_text(encoding="utf-8")
    assert report["state"] == "base_refreshed"
    assert report["projection_refresh_required"] is False
    assert report["candidate_head"] == candidate_head
    assert "maximum_total = 60" in merged
    assert all(f'id = "{identifier}"' in merged for identifier in ("base", "candidate", "lane"))
    assert (
        git(repo, "merge-base", "--is-ancestor", candidate_head, git(worktree, "rev-parse", "HEAD"))
        == ""
    )


def test_refresh_work_lane_base_plans_stale_candidate_base(tmp_path: Path) -> None:
    _, _, worktree, work_head, candidate_head = _stale_work_lane(tmp_path)

    report = refresh_work_lane_base(
        root=worktree,
        apply=False,
        authorized=False,
        expect_head=None,
    )

    assert report["ok"] is True
    assert report["state"] == "ready_to_refresh_base"
    assert report["branch"] == "work/feature"
    assert report["head"] == work_head
    assert report["candidate_head"] == candidate_head
    assert report["required_gaps"] == []


def test_refresh_work_lane_base_apply_rebases_current_lane(tmp_path: Path) -> None:
    repo, _, worktree, previous_head, candidate_head = _stale_work_lane(tmp_path)

    report = refresh_work_lane_base(
        root=worktree,
        apply=True,
        authorized=True,
        expect_head=previous_head,
    )

    refreshed_head = git(worktree, "rev-parse", "HEAD")
    assert report["ok"] is True
    assert report["state"] == "base_refreshed"
    assert report["branch"] == "work/feature"
    assert report["previous_head"] == previous_head
    assert report["head"] == refreshed_head
    assert report["candidate_head"] == candidate_head
    assert report["required_gaps"] == []
    assert refreshed_head != previous_head
    assert git(repo, "merge-base", "--is-ancestor", candidate_head, refreshed_head) == ""
    assert (worktree / "CANDIDATE.md").exists()
    assert (worktree / "FEATURE.md").exists()


def test_ssh_signing_transport_uses_launchd_agent_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[tuple[str, ...], dict[str, object]]] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((tuple(command), kwargs))
        if command[:2] == ["launchctl", "getenv"]:
            return subprocess.CompletedProcess(command, 0, "agent.sock\n", "")
        if command[:2] == ["ssh-add", "-T"]:
            return subprocess.CompletedProcess(
                command,
                0 if isinstance(kwargs.get("env"), dict) else 1,
                "",
                "",
            )
        raise AssertionError(command)

    monkeypatch.setattr(lane_refresh.subprocess, "run", fake_run)

    public_key = "signing-key.pub"
    agent_socket = "agent.sock"

    assert lane_refresh.ssh_signing_transport_ready(public_key) is True
    assert calls[0][0] == ("ssh-add", "-T", public_key)
    assert calls[1][0] == ("launchctl", "getenv", "SSH_AUTH_SOCK")
    assert calls[2][1]["env"] == {"SSH_AUTH_SOCK": agent_socket}
    monkeypatch.setattr(lane_refresh.subprocess, "run", lambda command, **_kwargs: subprocess.CompletedProcess(command, 0, "", ""))
    assert lane_refresh.ssh_signing_transport_ready(public_key) is True
    def unavailable(*_args: object, **_kwargs: object) -> None:
        raise OSError
    monkeypatch.setattr(lane_refresh.subprocess, "run", unavailable)
    assert lane_refresh.ssh_signing_transport_ready(public_key) is False


def test_refresh_work_lane_base_blocks_unavailable_file_backed_ssh_before_rebase(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, _, worktree, _, _ = _stale_work_lane(tmp_path)
    key = worktree / "keys" / "signing-key"
    key.parent.mkdir()
    key.write_text("private\n", encoding="utf-8")
    key.with_name("signing-key.pub").write_text("public\n", encoding="utf-8")
    git(worktree, "add", "keys")
    git(worktree, "-c", "user.name=Test User", "-c", "user.email=test@example.com", "commit", "-m", "add signing key fixture")
    previous_head = git(worktree, "rev-parse", "HEAD")
    original_run_git = lane_refresh.run_git
    rebase_calls: list[tuple[str, ...]] = []
    values = {"commit.gpgsign": "true", "gpg.format": "ssh", "user.signingkey": "keys/signing-key"}

    def signing_git(root: Path, *args: str, **kwargs: object) -> subprocess.CompletedProcess[str]:
        if args[:2] == ("config", "--get"):
            return subprocess.CompletedProcess(["git", *args], 0, values.get(args[-1], ""), "")
        if "rebase" in args:
            rebase_calls.append(args)
            return subprocess.CompletedProcess(["git", *args], 0, "", "")
        return original_run_git(root, *args, **kwargs)

    monkeypatch.setattr(
        lane_refresh, "ssh_signing_transport_ready", lambda _key: False, raising=False
    )
    report = lane_refresh.refresh_work_lane_base(
        root=worktree, apply=True, authorized=True, expect_head=previous_head,
        runtime=lane_refresh.LaneRefreshRuntime(run_git=signing_git),
    )

    assert report["required_gaps"] == ["refresh_signing_transport_unavailable"]
    assert rebase_calls == []
    assert git(worktree, "rev-parse", "HEAD") == previous_head


def test_refresh_work_lane_base_blocks_snapshot_moved_during_preflight(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, candidate, worktree, previous_head, _ = _stale_work_lane(tmp_path)

    def move_candidate(*_args: object, **_kwargs: object) -> list[str]:
        commit_fixture_file(candidate, "LATE.md", "# late\n", "advance candidate late")
        return []

    monkeypatch.setattr(lane_refresh, "_signing_preflight_gaps", move_candidate, raising=False)

    report = refresh_work_lane_base(
        root=worktree, apply=True, authorized=True, expect_head=previous_head
    )

    assert report["required_gaps"] == ["refresh_base_snapshot_stale:candidate"]
    assert git(worktree, "rev-parse", "HEAD") == previous_head


def test_refresh_work_lane_base_rechecks_configured_candidate_ref(tmp_path: Path) -> None:
    calls: list[tuple[str, ...]] = []

    def run_git(_root: Path, *args: str, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        stdout = {"stage/dev": "moved\n", "HEAD": "h1\n", "commit.gpgsign": "true", "gpg.format": "ssh", "user.signingkey": "missing"}.get(args[-1], "")
        return subprocess.CompletedProcess(["git", *args], 0, stdout, "")

    runtime = lane_refresh.LaneRefreshRuntime(
        load_branch_role_policy=lambda _root: SimpleNamespace(candidate_branch="stage/dev"),
        workspace_status=lambda _root: {
            "role": "work_lane", "dirty": False, "branch": "work/feature",
            "candidate": {"exists": True, "worktree_exists": True, "worktree_path": "candidate", "head": "c1"},
        },
        changed_paths=lambda _path: [], is_ancestor=lambda *_args: False, run_git=run_git,
    )
    report = lane_refresh.refresh_work_lane_base(
        root=tmp_path, apply=True, authorized=True, expect_head="h1", runtime=runtime,
    )

    assert report["required_gaps"] == ["refresh_base_snapshot_stale:candidate"]
    assert ("rev-parse", "stage/dev") in calls


def test_refresh_work_lane_base_does_not_overwrite_branch_moved_before_cas(
    tmp_path: Path,
) -> None:
    repo, _, worktree, previous_head, candidate_head = _stale_work_lane(tmp_path)
    original_run_git = lane_refresh.run_git

    def move_branch_before_cas(
        root: Path, *args: str, **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if args and args[0] == "update-ref":
            git(repo, "update-ref", "refs/heads/work/feature", candidate_head, previous_head)
        return original_run_git(root, *args, **kwargs)

    report = refresh_work_lane_base(
        root=worktree, apply=True, authorized=True, expect_head=previous_head,
        runtime=lane_refresh.LaneRefreshRuntime(run_git=move_branch_before_cas),
    )

    assert report["required_gaps"] == ["refresh_base_snapshot_stale:work_lane"]
    assert git(worktree, "rev-parse", "HEAD") == candidate_head


@pytest.mark.parametrize(("attach_code", "head", "gap"), [(1, "rebased", "refresh_base_worktree_attach_failed"), (0, "moved", "refresh_base_snapshot_stale:work_lane")])
def test_refresh_work_lane_base_rejects_attach_and_post_cas_races(tmp_path: Path, attach_code: int, head: str, gap: str) -> None:
    heads, ancestors = iter(("work", "work", "candidate", "rebased", head)), iter((False, True))
    def run(_root: Path, *args: str, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(["git", *args], attach_code if args == ("switch", "work/feature") else 0, f"{next(heads)}\n" if args[:1] == ("rev-parse",) else "", "attach")
    runtime = lane_refresh.LaneRefreshRuntime(load_branch_role_policy=lambda _root: SimpleNamespace(candidate_branch="candidate/dev"), workspace_status=lambda _root: {"role": "work_lane", "dirty": False, "branch": "work/feature", "candidate": {"exists": True, "worktree_exists": True, "worktree_path": "candidate", "head": "candidate"}}, changed_paths=lambda _path: [], is_ancestor=lambda *_args: next(ancestors), run_git=run)
    report = lane_refresh.refresh_work_lane_base(root=tmp_path, apply=True, authorized=True, expect_head="work", runtime=runtime)
    assert report["required_gaps"] == [gap]


def test_refresh_work_lane_base_rejects_noop_rebase_success(tmp_path: Path) -> None:
    _, _, worktree, previous_head, candidate_head = _stale_work_lane(tmp_path)
    original_run_git = lane_refresh.run_git

    def successful_noop_rebase(
        root: Path, *args: str, **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if args == (
            "-c",
            "rebase.updateRefs=false",
            "rebase",
            candidate_head,
            previous_head,
        ):
            return subprocess.CompletedProcess(["git", *args], 0, "", "")
        return original_run_git(root, *args, **kwargs)

    report = refresh_work_lane_base(
        root=worktree,
        apply=True,
        authorized=True,
        expect_head=previous_head,
        runtime=lane_refresh.LaneRefreshRuntime(run_git=successful_noop_rebase),
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["head"] == previous_head
    assert report["candidate_head"] == candidate_head
    assert report["required_gaps"] == ["refresh_base_postcondition_failed"]
    assert report["next_actions"] == [
        "inspect current Git ancestry and runner, signing, or hook diagnostics",
        "repair the replay environment and rerun ethos lane refresh-base",
    ]


def test_refresh_work_lane_base_apply_requires_authorization_and_expected_head(
    tmp_path: Path,
) -> None:
    _, _, worktree, _, _ = _stale_work_lane(tmp_path, commit_lane=False)

    report = refresh_work_lane_base(
        root=worktree,
        apply=True,
        authorized=False,
        expect_head=None,
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["authorization_required", "expect_head_required"]


@pytest.mark.parametrize("mode", ["nested_work_lane", "dirty_accepted_root"])
def test_start_work_lane_apply_requires_clean_accepted_root(tmp_path: Path, mode: str) -> None:
    repo = init_repo(tmp_path / "repo")
    root = repo
    name = "feature"
    worktree = tmp_path / "repo-work-feature"
    if mode == "nested_work_lane":
        root = tmp_path / "repo-work-current"
        name = "nested"
        worktree = tmp_path / "repo-work-nested"
        git(repo, "worktree", "add", "-b", "work/current", root.as_posix(), "dev")
    else:
        add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
        (repo / "README.md").write_text("# changed\n", encoding="utf-8")
    report = start_work_lane(
        root=root,
        name=name,
        path=worktree,
        holder_ref="agent:test:case:agent-test",
        apply=True,
    )
    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert "lane_start_requires_clean_accepted_root" in report["required_gaps"]
    assert not worktree.exists()
    if mode == "dirty_accepted_root":
        assert report["role"] == "accepted_root"
        assert report["dirty"] is True


def test_workspace_status_reports_runtime_binding_for_audited_checkout(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")

    status = workspace_status(repo)

    binding = status["runtime_binding"]
    assert binding["kind"] == "workspace_status_runtime_binding"
    assert binding["audit_root"] == repo.resolve().as_posix()
# fmt: on
    assert all(binding[key] for key in ("runner_module_path", "runner_source_root", "schema_source_root", "next_action"))
    assert isinstance(binding["advisory_gaps"], list)
    assert all(isinstance(binding[key], bool) for key in ("runner_matches_audit_root", "schema_matches_audit_root"))


def test_workspace_status_runtime_binding_warns_when_runner_is_external(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    external_runner = tmp_path / "external" / "packages" / "ethos" / "src" / "ethos" / "__init__.py"
    external_runner.parent.mkdir(parents=True)
    (tmp_path / "external" / "pyproject.toml").write_text(
        "[project]\nname='external'\n", encoding="utf-8"
    )
    external_runner.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        "ethos.adapters.repo.runtime.core.ethos.__file__", external_runner.as_posix()
    )

    status = workspace_status(repo)

    binding = status["runtime_binding"]
    assert binding["state"] == "external_current_runner"
    assert binding["runner_matches_audit_root"] is False
    assert "workspace_status_runner_source_differs_from_audit_root" in binding["advisory_gaps"]
    assert "package-bound runner" in binding["next_action"]


def test_workspace_status_marks_declared_external_adopter_runner(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    project = repo / ".ethos" / "project.toml"
    project.parent.mkdir(exist_ok=True)
    project.write_text(
        "[command_plane]\npublic = 'pixi run ethos'\n",
        encoding="utf-8",
    )
    external_runner = tmp_path / "external" / "packages" / "ethos" / "src" / "ethos" / "__init__.py"
    external_runner.parent.mkdir(parents=True)
    (tmp_path / "external" / "pyproject.toml").write_text(
        "[project]\nname='external'\n", encoding="utf-8"
    )
    external_runner.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        "ethos.adapters.repo.runtime.core.ethos.__file__", external_runner.as_posix()
    )

    binding = workspace_status(repo)["runtime_binding"]

    assert binding["state"] == "external_declared_runner"
    assert binding["advisory_gaps"] == []
    assert "declared external runner" in binding["next_action"]


def test_runtime_binding_lives_in_semantic_subpackage(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")

    binding = runtime_binding(repo)

    assert binding["kind"] == "workspace_status_runtime_binding"
    assert binding["audit_root"] == repo.resolve().as_posix()
