from __future__ import annotations

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
from tests.support.subprocesses import completed

type MonkeyPatch = pytest.MonkeyPatch
type GitResult = subprocess.CompletedProcess[str]
type DebtRecords = list[tuple[str, int]]


def _start(root, name, path=None):
    return start_work_lane(
        root=root,
        name=name,
        path=path,
        holder_ref="agent:test:case:agent-test",
        apply=True,
    )


def _refresh(root, head):
    return lane_refresh.refresh_work_lane_base(
        root=root, apply=True, authorized=True, expect_head=head
    )


def _guard(root, paths, editor):
    return prewrite.prewrite_guard(
        root=root, paths=paths, editor_root=editor, require_editor_root=True
    )


def _external_runner(tmp_path: Path) -> Path:
    runner = tmp_path / "external/packages/ethos/src/ethos/__init__.py"
    runner.parent.mkdir(parents=True)
    (tmp_path / "external/pyproject.toml").write_text("[project]\nname='external'\n")
    runner.write_text("")
    return runner


def _mock_refresh(
    monkeypatch: MonkeyPatch,
    run_git,
    candidate_branch: str,
    candidate_head: str,
    ancestor,
) -> None:
    monkeypatch.setattr(
        lane_refresh,
        "load_branch_role_policy",
        lambda _root: SimpleNamespace(candidate_branch=candidate_branch),
    )
    candidate = {
        "exists": True,
        "worktree_exists": True,
        "worktree_path": "candidate",
        "head": candidate_head,
    }
    monkeypatch.setattr(
        lane_refresh,
        "workspace_status",
        lambda _root: {
            "role": "work_lane",
            "dirty": False,
            "branch": "work/feature",
            "candidate": candidate,
        },
    )
    monkeypatch.setattr(lane_refresh, "changed_paths", lambda _path: [])
    monkeypatch.setattr(lane_refresh, "is_ancestor", ancestor)
    monkeypatch.setattr(lane_refresh, "run_git", run_git)


if TYPE_CHECKING:
    from pathlib import Path


def test_branch_role_policy_uses_configured_order() -> None:
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
    roles = {
        "release": "release_root",
        "integration": "accepted_root",
        "stage/integration": "candidate",
        "lane/feature": "work_lane",
        "review/feature": "submit_lane",
        "main": "other",
        "dev": "other",
        "candidate/dev": "other",
        "work/feature": "other",
        "submit/feature": "other",
    }
    assert [policy.role_for_branch(branch) for branch in roles] == list(roles.values())


def test_start_lane_uses_configured_role_policy(
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
    report = _start(repo, "feature", worktree)
    assert report["ok"] is True
    assert report["branch"] == "lane/feature"
    assert report["base"] == "stage/dev"
    assert git(worktree, "branch", "--show-current") == "lane/feature"


def test_existing_lane_binds_claim(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    _start(repo, "feature", worktree)
    report = bind_work_lane_claim(root=worktree, claim_id="sample-trust", apply=True)
    status = workspace_status(worktree)
    assert report["ok"] is True
    assert report["state"] == "bound"
    assert report["branch"] == "work/feature"
    assert report["holder_ref"] == "agent:test:case:agent-test"
    assert report["claim_id"] == "sample-trust"
    closeout = status["closeout_support"]
    assert closeout["supported"] is True
    assert closeout["branch"] == "work/feature"
    assert closeout["target_branch"] == "candidate/dev"
    assert closeout["operation"] == "land_to_candidate"
    assert closeout["holder_ref"] == "agent:test:case:agent-test"
    assert closeout["lease_epoch"] == 1
    assert closeout["claim_id"] == "sample-trust"
    assert closeout["claim_binding"] == "bound"
    assert closeout["required_gaps"] == []
    assert closeout["target_path"] == candidate.as_posix()
    assert closeout["lease_id"]


@pytest.mark.parametrize(
    ("editor_bound", "expected"),
    [(True, (True, "")), (False, (False, "editor_root_missing"))],
    ids=("matching-editor", "missing-editor"),
)
def test_prewrite_owned_lane_editor_binding(tmp_path, monkeypatch, editor_bound, expected):
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-owned"
    _start(repo, "owned", worktree)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    if editor_bound:
        monkeypatch.setattr(prewrite, "workspace_status", pytest.fail, raising=False)
        report = _guard(worktree, [worktree / "README.md"], worktree)
    else:
        report = prewrite_guard(root=worktree, paths=[worktree / "README.md"])
    assert (report["ok"], report["error"]) == expected
    assert report["role"] == "work_lane"


def test_prewrite_blocks_external_runner(tmp_path: Path, monkeypatch) -> None:
    repo = init_repo(tmp_path / "repo")
    worktree = tmp_path / "repo-work-owned"
    git(repo, "worktree", "add", "-b", "work/owned", worktree.as_posix(), "dev")
    product_marker = worktree / "packages" / "ethos" / "src" / "ethos" / "__init__.py"
    product_marker.parent.mkdir(parents=True)
    product_marker.write_text("", encoding="utf-8")
    external_runner = _external_runner(tmp_path)
    monkeypatch.setattr(
        "ethos.adapters.repo.runtime.core.ethos.__file__", external_runner.as_posix()
    )
    report = _guard(worktree, [worktree / "README.md"], worktree)
    assert report["ok"] is False
    assert report["error"] == "root_binding_mismatch"
    assert report["runtime_binding"]["product_audit_root"] is True
    assert report["runtime_binding"]["runner_matches_audit_root"] is False


@pytest.mark.parametrize(
    ("branch", "role"),
    [
        ("dev", "accepted_root"),
        ("main", "release_root"),
        ("candidate/dev", "candidate"),
        ("submit/review", "submit_lane"),
        ("feature/unknown", "other"),
        ("", "detached"),
    ],
    ids=("accepted", "release", "candidate", "submit", "other", "detached"),
)
def test_prewrite_blocks_protected_roles(tmp_path, branch, role):
    repo = init_repo(tmp_path / f"repo-{role}")
    if branch != "dev":
        git(repo, "checkout", *("--detach", "HEAD") if not branch else ("-b", branch))
    report = _guard(repo, [repo / "README.md"], repo)
    assert (report["ok"], report["role"], report["error"]) == (
        False,
        role,
        "protected_lane_prewrite_blocked",
    )


def test_start_lane_creates_worktree_and_lease(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    report = _start(repo, "feature", worktree)
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


def test_start_lane_defaults_sibling_path(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    expected = repo.with_name(f"{repo.name}-work-feature")
    report = _start(repo, "feature", None)
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
def test_start_lane_requires_ready_candidate(tmp_path: Path, mode: str, expected_gap: str) -> None:
    repo = init_repo(tmp_path / "repo")
    if mode == "worktree_missing":
        git(repo, "branch", "candidate/dev", "dev")
    elif mode == "worktree_dirty":
        candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
        (candidate / "README.md").write_text("# dirty candidate\n", encoding="utf-8")
    worktree = tmp_path / "repo-work-feature"
    report = _start(repo, "feature", worktree)
    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert expected_gap in report["required_gaps"]
    assert not worktree.exists()


def test_start_lane_uses_candidate_head(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    candidate_head = git(repo, "rev-parse", "candidate/dev")
    (repo / "README.md").write_text("# changed on dev\n", encoding="utf-8")
    commit_fixture_file(repo, "README.md", "# changed on dev\n", "advance dev only")
    worktree = tmp_path / "repo-work-feature"
    report = _start(repo, "feature", worktree)
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
    git(
        repo,
        "worktree",
        "add",
        "-b",
        "work/feature",
        worktree.as_posix(),
        "candidate/dev",
    )
    commit_fixture_file(candidate, candidate_path, "# candidate\n", "advance candidate")
    if commit_lane:
        commit_fixture_file(worktree, lane_path, "# feature\n", "feature work")
    return (
        repo,
        candidate,
        worktree,
        git(worktree, "rev-parse", "HEAD"),
        git(candidate, "rev-parse", "HEAD"),
    )


def _rules(root: Path, records: DebtRecords) -> None:
    template = (
        "[[quality.source_budget.debt.records]]\n"
        'id = "{}"\nowner = "test"\nreplacement = "test replacement"\n'
        'deletion_wave = "test"\nexpiry = "test"\nallowance = {}'
    )
    rules = root / ".ethos" / "rules.toml"
    rules.parent.mkdir(exist_ok=True)
    content = (
        "[quality.source_budget.debt]",
        f"maximum_total = {sum(allowance for _identifier, allowance in records)}",
        *(template.format(identifier, allowance) for identifier, allowance in records),
        '[gates.local-state-audit]\ncommand = "test"\nblocking = true',
        "",
    )
    rules.write_text("\n\n".join(content))


def _commit_rules(root: Path, records: DebtRecords, message: str, extra: str = "") -> None:
    _rules(root, records)
    path = root / ".ethos/rules.toml"
    path.write_text(path.read_text() + extra)
    commit_fixture_file(root, ".ethos/rules.toml", path.read_text(), message)


@pytest.mark.parametrize(
    ("candidate_record", "lane_record", "outside_change", "ok"),
    [
        ("candidate", "lane", False, True),
        ("shared", "shared", False, False),
        ("candidate", "lane", True, False),
    ],
)
def test_refresh_handles_budget_debt_conflicts(
    tmp_path: Path,
    candidate_record: str,
    lane_record: str,
    *,
    outside_change: bool,
    ok: bool,
) -> None:
    repo = init_repo(tmp_path / "repo")
    _commit_rules(repo, [("base", 10)], "declare source budget debt")
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    git(
        repo,
        "worktree",
        "add",
        "-b",
        "work/feature",
        worktree.as_posix(),
        "candidate/dev",
    )
    _commit_rules(
        candidate,
        [("base", 10), (candidate_record, 20)],
        "add candidate debt",
        extra="\n[unrelated]\nvalue = true\n" if outside_change else "",
    )
    _commit_rules(worktree, [("base", 10), (lane_record, 30)], "add lane debt")
    previous_head = git(worktree, "rev-parse", "HEAD")
    candidate_head = git(candidate, "rev-parse", "HEAD")
    report = _refresh(worktree, previous_head)
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
        git(
            repo,
            "merge-base",
            "--is-ancestor",
            candidate_head,
            git(worktree, "rev-parse", "HEAD"),
        )
        == ""
    )


def test_refresh_plans_stale_base(tmp_path: Path) -> None:
    _, _, worktree, work_head, candidate_head = _stale_work_lane(tmp_path)
    report = refresh_work_lane_base(root=worktree, apply=False, authorized=False, expect_head=None)
    assert report["ok"] is True
    assert report["state"] == "ready_to_refresh_base"
    assert report["branch"] == "work/feature"
    assert report["head"] == work_head
    assert report["candidate_head"] == candidate_head
    assert report["required_gaps"] == []


def test_refresh_rebases_lane(tmp_path: Path) -> None:
    repo, _, worktree, previous_head, candidate_head = _stale_work_lane(tmp_path)
    report = _refresh(worktree, previous_head)
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


def test_ssh_signing_uses_launchd_socket(
    monkeypatch: MonkeyPatch,
) -> None:
    calls: list[tuple[tuple[str, ...], dict[str, object]]] = []

    def fake_run(command: list[str], **kwargs: object) -> GitResult:
        calls.append((tuple(command), kwargs))
        if command[:2] == ["launchctl", "getenv"]:
            return completed("agent.sock\n")
        if command[:2] == ["ssh-add", "-T"]:
            return completed(returncode=0 if isinstance(kwargs.get("env"), dict) else 1)
        raise AssertionError(command)

    monkeypatch.setattr(lane_refresh.subprocess, "run", fake_run)
    public_key = "signing-key.pub"
    agent_socket = "agent.sock"
    assert lane_refresh.ssh_signing_transport_ready(public_key) is True
    assert calls[0][0] == ("ssh-add", "-T", public_key)
    assert calls[1][0] == ("launchctl", "getenv", "SSH_AUTH_SOCK")
    assert calls[2][1]["env"] == {"SSH_AUTH_SOCK": agent_socket}
    monkeypatch.setattr(
        lane_refresh.subprocess,
        "run",
        lambda _command, **_kwargs: completed(),
    )
    assert lane_refresh.ssh_signing_transport_ready(public_key) is True

    def unavailable(*_args: object, **_kwargs: object) -> None:
        raise OSError

    monkeypatch.setattr(lane_refresh.subprocess, "run", unavailable)
    assert lane_refresh.ssh_signing_transport_ready(public_key) is False


def test_refresh_blocks_unavailable_signing(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    _, _, worktree, _, _ = _stale_work_lane(tmp_path)
    key = worktree / "keys/signing-key"
    key.parent.mkdir()
    key.write_text("private\n")
    git(worktree, "add", "keys/signing-key")
    commit_fixture_file(worktree, "keys/signing-key.pub", "public\n", "add key")
    previous_head = git(worktree, "rev-parse", "HEAD")
    original = lane_refresh.run_git
    rebase_calls = []
    values = {
        "commit.gpgsign": "true",
        "gpg.format": "ssh",
        "user.signingkey": "keys/signing-key",
    }

    def guarded_git(root, *args, **kwargs):
        if args[:2] == ("config", "--get"):
            return completed(values.get(args[-1], ""))
        if "rebase" in args:
            rebase_calls.append(args)
        return original(root, *args, **kwargs)

    monkeypatch.setattr(lane_refresh, "ssh_signing_transport_ready", lambda _key: False)
    monkeypatch.setattr(lane_refresh, "run_git", guarded_git)
    report = _refresh(worktree, previous_head)
    assert report["required_gaps"] == ["refresh_signing_transport_unavailable"]
    assert rebase_calls == []
    assert git(worktree, "rev-parse", "HEAD") == previous_head


def test_refresh_blocks_candidate_snapshot_move(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    _, candidate, worktree, previous_head, _ = _stale_work_lane(tmp_path)

    def move_candidate(*_args: object, **_kwargs: object) -> list[str]:
        commit_fixture_file(candidate, "LATE.md", "# late\n", "advance late")
        return []

    monkeypatch.setattr(lane_refresh, "_signing_preflight_gaps", move_candidate)
    report = _refresh(worktree, previous_head)
    assert report["required_gaps"] == ["refresh_base_snapshot_stale:candidate"]
    assert git(worktree, "rev-parse", "HEAD") == previous_head


def test_refresh_blocks_work_lane_cas_move(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    repo, _, worktree, previous_head, candidate_head = _stale_work_lane(tmp_path)
    original = lane_refresh.run_git

    def move_branch(root, *args, **kwargs):
        if args[:1] == ("update-ref",):
            git(repo, "update-ref", "refs/heads/work/feature", candidate_head, previous_head)
        return original(root, *args, **kwargs)

    monkeypatch.setattr(lane_refresh, "run_git", move_branch)
    report = _refresh(worktree, previous_head)
    assert report["required_gaps"] == ["refresh_base_snapshot_stale:work_lane"]
    assert git(worktree, "rev-parse", "HEAD") == candidate_head


def test_refresh_rejects_noop_rebase(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    _, _, worktree, previous_head, candidate_head = _stale_work_lane(tmp_path)
    original = lane_refresh.run_git

    def noop_rebase(root, *args, **kwargs):
        if args == ("-c", "rebase.updateRefs=false", "rebase", candidate_head, previous_head):
            return completed()
        return original(root, *args, **kwargs)

    monkeypatch.setattr(lane_refresh, "run_git", noop_rebase)
    report = _refresh(worktree, previous_head)
    assert (report["ok"], report["state"], report["head"], report["candidate_head"]) == (
        False,
        "blocked",
        previous_head,
        candidate_head,
    )
    assert report["required_gaps"] == ["refresh_base_postcondition_failed"]
    assert report["next_actions"] == [
        "inspect current Git ancestry and runner, signing, or hook diagnostics",
        "repair the replay environment and rerun ethos lane refresh-base",
    ]


def test_refresh_rechecks_candidate_ref(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    calls: list[tuple[str, ...]] = []

    def run_git(_root: Path, *args: str, **_kwargs: object) -> GitResult:
        calls.append(args)
        stdout = {
            "stage/dev": "moved\n",
            "HEAD": "h1\n",
            "commit.gpgsign": "true",
            "gpg.format": "ssh",
            "user.signingkey": "missing",
        }.get(args[-1], "")
        return completed(stdout)

    _mock_refresh(monkeypatch, run_git, "stage/dev", "c1", lambda *_args: False)
    report = _refresh(tmp_path, "h1")
    assert report["required_gaps"] == ["refresh_base_snapshot_stale:candidate"]
    assert ("rev-parse", "stage/dev") in calls


@pytest.mark.parametrize(
    ("attach_code", "head", "gap"),
    [
        (1, "rebased", "refresh_base_worktree_attach_failed"),
        (0, "moved", "refresh_base_snapshot_stale:work_lane"),
    ],
)
def test_refresh_rejects_attach_and_cas_races(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    attach_code: int,
    head: str,
    gap: str,
) -> None:
    heads, ancestors = (
        iter(("work", "work", "candidate", "rebased", head)),
        iter((False, True)),
    )

    def run(_root: Path, *args: str, **_kwargs: object) -> GitResult:
        return completed(
            f"{next(heads)}\n" if args[:1] == ("rev-parse",) else "",
            "attach",
            attach_code if args == ("switch", "work/feature") else 0,
        )

    _mock_refresh(monkeypatch, run, "candidate/dev", "candidate", lambda *_args: next(ancestors))
    report = _refresh(tmp_path, "work")
    assert report["required_gaps"] == [gap]


def test_refresh_requires_authorization_and_head(
    tmp_path: Path,
) -> None:
    _, _, worktree, _, _ = _stale_work_lane(tmp_path, commit_lane=False)
    report = refresh_work_lane_base(root=worktree, apply=True, authorized=False, expect_head=None)
    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["authorization_required", "expect_head_required"]


@pytest.mark.parametrize("mode", ["nested_work_lane", "dirty_accepted_root"])
def test_start_lane_requires_clean_accepted_root(tmp_path: Path, mode: str) -> None:
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
    report = _start(root, name, worktree)
    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert "lane_start_requires_clean_accepted_root" in report["required_gaps"]
    assert not worktree.exists()
    if mode == "dirty_accepted_root":
        assert report["role"] == "accepted_root"
        assert report["dirty"] is True


def test_status_runtime_binding_states(tmp_path: Path, monkeypatch) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    binding = workspace_status(repo)["runtime_binding"]
    assert binding["kind"] == "workspace_status_runtime_binding"
    assert binding["audit_root"] == repo.resolve().as_posix()
    paths = {"runner_module_path", "runner_source_root", "schema_source_root"}
    assert all(map(binding.get, paths | {"next_action"}))
    assert isinstance(binding["advisory_gaps"], list)
    assert all(
        isinstance(binding[key], bool)
        for key in ("runner_matches_audit_root", "schema_matches_audit_root")
    )
    assert runtime_binding(repo) == binding
    monkeypatch.setattr(
        "ethos.adapters.repo.runtime.core.ethos.__file__",
        _external_runner(tmp_path).as_posix(),
    )
    external = workspace_status(repo)["runtime_binding"]
    assert external["state"] == "external_current_runner"
    assert external["runner_matches_audit_root"] is False
    gap = "workspace_status_runner_source_differs_from_audit_root"
    assert gap in external["advisory_gaps"]
    assert "package-bound runner" in external["next_action"]
    project = repo / ".ethos/project.toml"
    project.parent.mkdir(exist_ok=True)
    project.write_text("[command_plane]\npublic = 'pixi run ethos'\n")
    declared = workspace_status(repo)["runtime_binding"]
    assert declared["state"] == "external_declared_runner"
    assert declared["advisory_gaps"] == []
    assert "declared external runner" in declared["next_action"]
