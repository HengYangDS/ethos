"""Native parent provenance distinguishes coexisting official Change intent."""

from pathlib import Path

import pytest

import ethos.adapters.mutation.lane_lifecycle.start as lane_start
from ethos.adapters.mutation.lane_lifecycle.archive.command import archive_change
from ethos.adapters.mutation.proof import proof_artifact_root
from ethos.adapters.mutation.proof import proof_attestation
from ethos.adapters.mutation.proof import proof_for_repository_transition
from ethos.adapters.mutation.proof import proof_gaps
from ethos.adapters.mutation.proof_admission import proof_attestation as query_proof
from ethos.adapters.openspec.cli import openspec_base_command
from ethos.adapters.openspec.cli import run_json
from ethos.adapters.openspec.commitment import load_openspec_commitment
from ethos.adapters.openspec.governance import openspec_governance_report
from ethos.adapters.openspec.selection import selected_change
from ethos.adapters.openspec.selection import selection_gaps
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.value import mutable_json
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import create_change_source_lane
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import prepared_work_lane
from tests.support.governed_repository import start_adopted_candidate
from tests.support.governed_repository import write_active_commitment
from tests.support.governed_repository import write_test_profile
from tests.support.openspec_lifecycle import native_merge_fixture
from tests.support.proof import declare_native_proof_checks
from tests.support.runtime_scenarios import install_fixture_hook_runtime
from tests.support.semantic import reissue_attestation


def _prove(root: Path, head: str, *selection: str) -> dict:
    """Execute the same native full-proof contract for each lifecycle consumer."""
    report = run_ethos(
        "prove", *selection, "--full", "--execute", "--expect-head", head, "--json", cwd=root
    )
    assert report["verdict"] == "pass", report
    assert report["data"]["attestation"]["subject"] == f"git:commit:{head}"
    return report["data"]["attestation"]


def _archive(root: Path, head: str, change: str) -> str:
    """Archive with real proof, then prove the resulting exact source."""
    _prove(root, head, "--change", change)
    report = archive_change(root=root, change=change, expect_head=head, apply=True)
    assert report["required_gaps"] == ["proof_not_proven"], report
    archived = git(root, "rev-parse", "HEAD")
    _prove(root, archived, "--change", change)
    return archived


@pytest.fixture
def pending_merge(tmp_path: Path) -> Path:
    """Reproduce independent open Changes with a real unresolved native merge."""
    return native_merge_fixture(tmp_path)


@pytest.mark.parametrize(
    "case", ["valid", "missing", "corrupt", "unrelated", "historical", "ambiguous"]
)
def test_lane_birth_selection_uses_only_valid_applicable_native_evidence(
    tmp_path, monkeypatch, case
):
    """Native effects bound inherited history; timestamps and unrelated evidence do not."""
    repo = init_git_repo(tmp_path / "repo")
    write_test_profile(repo)
    commit_fixture(repo, "declare repository identity")
    base = git(repo, "rev-parse", "HEAD")
    incoming = repo / "openspec/changes/active/tasks.md"
    incoming.parent.mkdir(parents=True)
    incoming.write_text("- [ ] Incoming contribution\n")
    commit_fixture(repo, "incoming active intent")
    side = git(repo, "rev-parse", "HEAD")
    merge = git(repo, "commit-tree", "HEAD^{tree}", "-p", base, "-p", side, "-m", "merge")
    git(repo, "reset", "--hard", merge)
    branch = "work/native"
    ref = f"refs/heads/{branch}"

    def start(head):
        git(repo, "update-ref", "refs/heads/candidate/dev", head)
        effect = GitEffect(
            updates={ref: GitRefUpdate(expected="0" * len(head), desired=head)},
            assertions={"refs/heads/candidate/dev": head},
        )
        plan = compile_observed_git_effect(
            repo,
            None,
            effect,
            head=git(repo, "rev-parse", "HEAD"),
            policy={
                "operation": "lane.start",
                "subject": branch,
                "holder_ref": "agent:test:case:agent-test",
                "candidate_branch": "candidate/dev",
            },
        )
        execute_git_effect(repo, plan, issuer="agent:test:case:agent-test")

    if case == "ambiguous":
        start(base)
        git(repo, "update-ref", "-d", ref, base)
    start(merge)
    git(repo, "checkout", branch)
    selected_root, records = read_attestation_set(repo)
    if case in {"missing", "corrupt", "unrelated"}:
        (record,) = (record for record in records if record.predicate == "effect:git-ref-update")
        if case == "corrupt":
            record = reissue_attestation(
                record, body=record.payload.body | {"input_digest": "corrupt"}
            )
        replacement = () if case == "missing" else (record,)
        monkeypatch.setattr(
            "ethos.adapters.openspec.selection.read_attestation_set",
            lambda _root: (selected_root, replacement),
        )
        if case == "unrelated":
            git(repo, "checkout", "-b", "work/other")
    rows = [{"name": "active", "status": "in-progress"}]
    revision = base if case == "historical" else merge
    expected = "active" if case in {"valid", "historical"} else None
    assert selected_change(rows, None, root=repo, tree_ref=revision) == expected
    gaps = selection_gaps(rows, None, root=repo, tree_ref=revision)
    assert gaps == (
        []
        if expected
        else ["openspec_change_provenance_unresolved"]
        if case in {"corrupt", "ambiguous"}
        else ["openspec_active_change_missing"]
    )
    assert selected_change(rows, "active", root=repo, tree_ref=revision) == "active"


@pytest.mark.parametrize("mode", ["pending", "committed", "explicit"])
def test_native_merge_selects_exact_intent_without_consuming_incoming_progress(pending_merge, mode):
    """Visible incoming intent is not a second contender for the lane operation."""
    work = pending_merge
    if mode == "committed":
        (work / "README.md").write_text("# Combined contribution\n")
        commit_fixture(work, "feat: reconcile both contributions")
    requested = "static-delivery" if mode == "explicit" else None
    expected = requested or "publication"
    before = git(work, "ls-files", "--stage")
    report = openspec_governance_report(
        work, change=requested, lifecycle=True, changed_paths=("README.md",)
    )
    assert report["verdict"] == "pass", report["required_gaps"]
    assert report["change"] == expected
    assert [row["name"] for row in report["lifecycle"]["changes"]] == [expected]
    assert load_openspec_commitment(work, change_id=requested).id == f"change:{expected}"
    tasks = work / "openspec/changes/static-delivery/tasks.md"
    assert "[ ]" in tasks.read_text()
    assert git(work, "ls-files", "--stage") == before


def test_public_pending_status_names_native_recovery_not_rebase_or_itself(pending_merge):
    """The public reader must not turn a resolvable merge into a status loop."""
    report = run_ethos("status", "--json", cwd=pending_merge)
    assert "merge_in_progress" in report["required_gaps"], report
    assert not any(
        "ambiguous" in gap or "change_mismatch" in gap for gap in report["required_gaps"]
    )
    assert report["next_action"].startswith("ethos lane refresh-base --strategy merge")
    assert "--apply" not in report["next_action"]


@pytest.mark.parametrize("state", ["committed", "uncommitted", "tasks-complete"])
def test_multiple_lane_changes_remain_ambiguous(pending_merge, state):
    """Commit, merge and task progress cannot choose between two own intents."""
    if state == "committed":
        git(pending_merge, "merge", "--abort")
    if state == "tasks-complete":
        for change in ("static-delivery", "publication"):
            tasks = pending_merge / f"openspec/changes/{change}/tasks.md"
            tasks.write_text(tasks.read_text().replace("[ ]", "[x]"))
    write_active_commitment(pending_merge, change_id="second-local")
    if state == "committed":
        commit_fixture(pending_merge, "feat: author competing local intent")
    report = openspec_governance_report(pending_merge, lifecycle=True)
    assert report["verdict"] == "block", report
    assert any("ambiguous" in gap for gap in report["required_gaps"])


def _declare_executable_checks(work: Path) -> None:
    """Use distinct real checks rather than synthetic proof success."""
    verify = (
        "from pathlib import Path; "
        "assert Path('README.md').read_text() == '# Combined publication\\n'; "
        "print('selected-lane-source-verified')"
    )
    validate = (
        "from pathlib import Path; import tomllib; "
        "registry = tomllib.loads(Path('system/gates.toml').read_text()); "
        "assert len(registry['gates']) == 2; print('gate-policy-verified')"
    )
    declare_native_proof_checks(work, test=verify, typecheck=validate)


def test_new_lane_selects_active_intent_after_inherited_archive(pending_merge, monkeypatch):
    """One source tree has different authoring ownership in old and new lanes."""
    work = pending_merge
    (work / "README.md").write_text("# Combined publication\n")
    _declare_executable_checks(work)
    tasks = work / "openspec/changes/publication/tasks.md"
    tasks.write_text(tasks.read_text().replace("[ ]", "[x]"))
    source_head = commit_fixture(work, "feat: finish local publication")
    head = _archive(work, source_head, "publication")
    assert openspec_governance_report(work, lifecycle=True)["change"] == "publication"
    assert load_openspec_commitment(work, tree_ref=head).id == "change:publication"
    previous = proof_attestation(work, head)
    assert previous is not None
    repo, candidate = work.parent / "repo", work.parent / "repo-candidate-dev"
    for target in (repo, candidate):
        git(target, "reset", "--hard", head)
    install_fixture_hook_runtime(repo)
    next_lane = work.parent / "next-lane"
    with monkeypatch.context() as supply:
        supply.setattr(lane_start, "require_runtime_wheel_provenance", lambda: None)
        supply.setattr(lane_start, "install_hook_launchers", install_fixture_hook_runtime)
        started = run_ethos(
            "lane",
            "start",
            "next",
            "--path",
            str(next_lane),
            "--holder-ref",
            "agent:test:case:agent-test",
            "--apply",
            "--json",
            cwd=repo,
        )
    assert started["verdict"] == "pass", started
    assert git(next_lane, "rev-parse", "HEAD") == head
    report = run_ethos(
        "lane",
        "prewrite",
        "openspec/changes/static-delivery/tasks.md",
        "--editor-root",
        str(next_lane),
        "--require-editor-root",
        "--json",
        cwd=next_lane,
    )
    assert report["verdict"] == "pass", report
    scope = report["data"]["material_scope"]
    assert scope["changes"] == [
        {"name": "static-delivery", "path": "openspec/changes/static-delivery"}
    ]
    assert scope["covered_paths"] == [
        {"path": "openspec/changes/static-delivery/tasks.md", "changes": ["static-delivery"]}
    ]
    for arguments in (("plan",), ("plan", "--change", "static-delivery")):
        planned = run_ethos(*arguments, "--json", cwd=next_lane)
        assert planned["verdict"] == "pass", planned
        assert planned["data"]["commitment"]["id"] == "change:static-delivery"
    assert proof_gaps(next_lane, head) == ["proof_lane_mismatch"]
    for arguments in ((), ("--change", "static-delivery")):
        _prove(next_lane, head, *arguments)
        attestation = proof_attestation(next_lane, head)
        assert attestation is not None
        assert attestation.id != previous.id
        plan = mutable_json(attestation.payload.body["plan"])
        assert plan["commitment"]["id"] == "change:static-delivery"
        expected = lease_generation(leases_by_branch(next_lane)["work/next"])
        assert plan["facts"]["values"]["lease_generation"] == mutable_json(expected)
        assert plan["facts"]["values"]["change_id"] == "static-delivery"
        assert proof_gaps(next_lane, head) == []
    assert proof_attestation(work, head) == previous


@pytest.mark.parametrize("command", [("lane", "prewrite"), ("hook", "admit", "pre-tool")])
def test_exact_official_artifacts_continue_after_second_change_creation(
    tmp_path, monkeypatch, command
):
    """Official creation remains editable without selecting unrelated product work."""
    root = prepared_work_lane(tmp_path).worktree
    change = "openspec/changes/second-local"
    arguments = ("--editor-root", str(root), "--require-editor-root", "--json")
    before = run_ethos(*command, f"{change}/.openspec.yaml", *arguments, cwd=root)
    assert before["verdict"] == "pass"
    base = openspec_base_command()
    assert base
    created = run_json(root, base, ("new", "change", "second-local", "--json"))
    assert created["exit_code"] == 0, created
    target = f"{change}/proposal.md"
    admitted = run_ethos(*command, target, *arguments, cwd=root)
    scope = admitted["data"] if command[0] == "lane" else admitted["data"]["admission"]
    assert scope["material_scope"]["state"] == "official_change_bootstrap"
    assert scope["material_scope"]["covered_paths"] == [
        {"path": target, "changes": ["second-local"]}
    ]
    for extra in ("README.md", "openspec/changes/fixture-change/tasks.md"):
        blocked = run_ethos_blocked(*command, target, extra, *arguments, cwd=root)
        rejected = blocked["data"] if command[0] == "lane" else blocked["data"]["admission"]
        assert rejected["openspec"]["change"] is None
    assert not (root / target).exists()
    with monkeypatch.context() as selected:
        selected.setenv("ETHOS_CHANGE", "fixture-change")
        rejected = run_ethos_blocked(*command, target, *arguments, cwd=root)
        report = rejected["data"] if command[0] == "lane" else rejected["data"]["admission"]
        assert report["openspec"]["change"] == "fixture-change"
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:other")
    blocked = run_ethos_blocked(*command, target, *arguments, cwd=root)
    assert any("lease_holder_mismatch" in gap for gap in blocked["required_gaps"])
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    write_active_commitment(root, change_id="second-local")
    valid = run_ethos(*command, target, *arguments, cwd=root)
    assert valid["verdict"] == "pass"
    before_commit = git(root, "rev-parse", "HEAD")
    committed = commit_fixture(root, "feat: complete second intent")
    assert committed != before_commit
    blocked = run_ethos_blocked(*command, "README.md", *arguments, cwd=root)
    assert blocked["next_action"] == "openspec list --json"
    assert blocked["user_decision_required"] is True
    status = run_ethos("status", "--json", cwd=root)
    assert status["next_action"] == "openspec list --json"
    assert status["user_decision_required"] is True
    assert load_openspec_commitment(root, change_id="second-local", tree_ref=committed)


@pytest.fixture
def completed_product_work(tmp_path, monkeypatch):
    """Prepare two completed official intents above accepted executable checks."""
    repo, candidate = start_adopted_candidate(tmp_path)
    _declare_executable_checks(repo)
    head = commit_fixture(repo, "test: declare native verification before authoring")
    git(candidate, "reset", "--hard", head)
    install_fixture_hook_runtime(repo)
    work = create_change_source_lane(
        repo, tmp_path / "work", base_ref="candidate/dev", holder_ref="agent:test:case:agent-test"
    )
    write_active_commitment(work, change_id="second-local")
    delta = work / "openspec/changes/second-local/specs/contracts/spec.md"
    delta.write_text(delta.read_text().replace("Fixture change", "Second contribution"))
    for tasks in (work / "openspec/changes").glob("*/tasks.md"):
        tasks.write_text(tasks.read_text().replace("[ ]", "[x]"))
    commit_fixture(work, "feat: declare completed contributions")
    monkeypatch.setenv("ETHOS_CHANGE", "second-local")
    return repo, candidate, work


def test_process_intent_carries_product_work_through_native_integration(
    completed_product_work, monkeypatch
):
    """One selection spans authoring, proof, archive and both native CAS boundaries."""
    repo, candidate, work = completed_product_work
    args = ("README.md", "--editor-root", str(work), "--require-editor-root", "--json")
    for command in (("lane", "prewrite"), ("hook", "admit", "pre-tool")):
        admitted = run_ethos(*command, *args, cwd=work)
        assert admitted["verdict"] == "pass", admitted
    (work / "README.md").write_text("# Combined publication\n")
    head = commit_fixture(work, "feat: integrate selected contribution")
    for choice, expected in (
        ((), "second-local"),
        (("--change", "fixture-change"), "fixture-change"),
    ):
        planned = run_ethos("plan", *choice, "--json", cwd=work)
        assert planned["data"]["commitment"]["id"] == f"change:{expected}"
    _prove(work, head)
    selected = proof_attestation(work, head)
    monkeypatch.setenv("ETHOS_CHANGE", "fixture-change")
    assert proof_gaps(work, head) == ["proof_not_proven"]
    monkeypatch.setenv("ETHOS_CHANGE", "second-local")
    before = git(work, "ls-files", "--stage")
    arguments = (
        "lane",
        "archive-change",
        "--change",
        "fixture-change",
        "--expect-head",
        head,
        "--apply",
        "--json",
    )
    denied = run_ethos_blocked(*arguments, cwd=work)
    assert denied["required_gaps"] == ["proof_not_proven"]
    assert "--change fixture-change" in denied["next_action"]
    assert (git(work, "rev-parse", "HEAD"), git(work, "status", "--porcelain")) == (head, "")
    assert git(work, "ls-files", "--stage") == before
    other_id = _prove(work, head, "--change", "fixture-change")["id"]
    observed, gaps = proof_for_repository_transition(work, head, attestation_id=other_id)
    assert (observed.id, gaps) == (other_id, [])
    assert query_proof(
        work,
        head,
        store=proof_artifact_root(work),
        attestation_id=other_id,
        change_id="second-local",
    ) == (None, ["proof_attestation_intent_mismatch"])
    assert proof_gaps(work, head) == []
    assert proof_attestation(work, head) == selected
    assert selected.commitment_digest == load_openspec_commitment(work).digest()
    for key, value, gap in (
        ("ETHOS_ACTOR", "agent:test:foreign", "holder"),
        ("ETHOS_CHANGE", "missing", "requested_change_missing"),
    ):
        with monkeypatch.context() as invalid:
            invalid.setenv(key, value)
            denied = run_ethos_blocked("lane", "prewrite", *args, cwd=work)
            assert any(gap in item for item in denied["required_gaps"])

    tasks = work / "openspec/changes/second-local/tasks.md"
    preserved = tasks.read_bytes()
    monkeypatch.setenv("ETHOS_CHANGE", "missing")
    run_ethos_blocked(*arguments, cwd=work)
    assert not (work / "openspec/changes/fixture-change").exists()
    assert tasks.read_bytes() == preserved
    assert run_ethos_blocked(*arguments, cwd=work)["required_gaps"] == ["proof_not_proven"]
    monkeypatch.setenv("ETHOS_CHANGE", "fixture-change")
    head = _archive(work, git(work, "rev-parse", "HEAD"), "second-local")
    _prove(work, head, "--change", "fixture-change")
    canonical = (work / "openspec/specs/contracts/spec.md").read_text()
    assert all(
        f"### Requirement: {name}" in canonical
        for name in ("Fixture change", "Second contribution")
    )
    run_ethos("land", "--apply", "--authorize", "--expect-head", head, "--json", cwd=work)
    run_ethos(
        "land",
        "--closeout",
        "--apply",
        "--authorize",
        "--expect-head",
        git(repo, "rev-parse", "HEAD"),
        "--candidate-head",
        head,
        "--json",
        cwd=repo,
    )
    assert git(repo, "rev-parse", "HEAD") == git(candidate, "rev-parse", "HEAD") == head
    monkeypatch.delenv("ETHOS_CHANGE")
    planned = run_ethos("plan", "--change", "second-local", "--json", cwd=work)
    assert planned["data"]["commitment"]["id"] == "change:second-local"
