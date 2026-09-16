"""Native parent provenance distinguishes coexisting official Change intent."""

import json
import sys
from pathlib import Path

import pytest

import ethos.adapters.mutation.lane_lifecycle.start as lane_start
from ethos.adapters.mutation.lane_lifecycle.archive.command import archive_change
from ethos.adapters.mutation.proof import proof_attestation
from ethos.adapters.mutation.proof import proof_gaps
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
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_active_commitment
from tests.support.governed_repository import write_test_profile
from tests.support.openspec_lifecycle import native_merge_fixture
from tests.support.runtime_scenarios import install_fixture_hook_runtime
from tests.support.semantic import reissue_attestation


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
        selected = tuple(
            record for record in records if record.predicate == "effect:git-ref-update"
        )
        assert len(selected) == 1
        record = selected[0]
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


def test_pending_merge_selects_lane_intent_without_consuming_incoming_progress(pending_merge):
    """Visible incoming intent is not a second contender for the lane operation."""
    work = pending_merge
    before = git(work, "ls-files", "--stage")
    report = openspec_governance_report(work, lifecycle=True, changed_paths=("README.md",))
    assert report["verdict"] == "pass", report["required_gaps"]
    assert report["change"] == "publication"
    assert [row["name"] for row in report["lifecycle"]["changes"]] == ["publication"]
    assert load_openspec_commitment(work).id == "change:publication"
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


def test_explicit_change_observes_only_its_native_status(pending_merge):
    """Explicit selection does not reuse the selected status for other Changes."""
    report = openspec_governance_report(
        pending_merge, change="static-delivery", lifecycle=True, changed_paths=()
    )
    assert report["verdict"] == "pass", report["required_gaps"]
    assert report["change"] == "static-delivery"


def test_merge_first_parent_retains_selection_after_native_completion(pending_merge):
    """Completing the merge does not erase its lane-side intent provenance."""
    (pending_merge / "README.md").write_text("# Combined contribution\n")
    commit_fixture(pending_merge, "feat: reconcile both contributions")
    report = openspec_governance_report(pending_merge, lifecycle=True)
    assert report["verdict"] == "pass", report["required_gaps"]
    assert report["change"] == "publication"


def test_multiple_lane_changes_remain_ambiguous(pending_merge):
    """A native parent relation cannot justify choosing between two own intents."""
    git(pending_merge, "merge", "--abort")
    write_active_commitment(pending_merge, change_id="second-local")
    commit_fixture(pending_merge, "feat: author competing local intent")
    report = openspec_governance_report(pending_merge, lifecycle=True)
    assert report["verdict"] == "block"
    assert any("ambiguous" in gap for gap in report["required_gaps"])


def test_pending_merge_does_not_hide_new_uncommitted_local_intent(pending_merge):
    """Parent attribution must not discard newly authored working-tree intent."""
    write_active_commitment(pending_merge, change_id="second-local")
    report = openspec_governance_report(pending_merge, lifecycle=True)
    assert report["verdict"] == "block", report
    assert any("ambiguous" in gap for gap in report["required_gaps"])


def test_unresolved_parent_attribution_cannot_fall_back_to_task_counts(pending_merge):
    """Selection failure and its public gap use the same contribution meaning."""
    incoming_tasks = pending_merge / "openspec/changes/static-delivery/tasks.md"
    incoming_tasks.write_text(incoming_tasks.read_text().replace("[ ]", "[x]"))
    ours = pending_merge / "openspec/changes/publication/tasks.md"
    ours.write_text(ours.read_text().replace("[ ]", "[x]"))
    write_active_commitment(pending_merge, change_id="second-local")
    report = openspec_governance_report(pending_merge, lifecycle=True)
    assert report["verdict"] == "block", report
    assert any("ambiguous" in gap for gap in report["required_gaps"])


def test_archived_lane_intent_does_not_select_the_remaining_incoming_change(
    pending_merge, monkeypatch
):
    """Archiving the local contribution cannot turn imported tasks into local intent."""
    work = pending_merge
    (work / "README.md").write_text("# Combined publication\n")
    tasks = work / "openspec/changes/publication/tasks.md"
    tasks.write_text(tasks.read_text().replace("[ ]", "[x]"))
    commit_fixture(work, "feat: finish local publication")
    monkeypatch.setattr(
        "ethos.adapters.mutation.lane_lifecycle.archive.command.proof_gaps", lambda *_args: []
    )
    archived = archive_change(
        root=work, change="publication", expect_head=git(work, "rev-parse", "HEAD"), apply=True
    )
    assert archived["verdict"] == "pass", archived
    report = openspec_governance_report(work, lifecycle=True)
    assert report["change"] == "publication", report
    assert load_openspec_commitment(work, tree_ref=git(work, "rev-parse", "HEAD")).id == (
        "change:publication"
    )


def _declare_executable_checks(work: Path) -> None:
    """Use distinct real checks rather than synthetic proof success."""
    profile = work / ".ethos/profile.toml"
    verify = (
        "from pathlib import Path; "
        "assert Path('README.md').read_text() == '# Combined publication\\n'; "
        "print('selected-lane-source-verified')"
    )
    validate = (
        "from pathlib import Path; import tomllib; "
        "profile = tomllib.loads(Path('.ethos/profile.toml').read_text()); "
        "assert len(profile['proof']['gates']) == 2; print('gate-policy-verified')"
    )
    profile.write_text(
        profile.read_text()
        .replace(
            'command = ["sample", "test"]',
            "command = " + json.dumps([sys.executable, "-c", verify]),
        )
        .replace(
            'command = ["sample", "typecheck"]',
            "command = " + json.dumps([sys.executable, "-c", validate]),
        )
    )


def test_new_lane_selects_active_intent_after_inherited_archive(pending_merge, monkeypatch):
    """One source tree has different authoring ownership in old and new lanes."""
    work = pending_merge
    (work / "README.md").write_text("# Combined publication\n")
    _declare_executable_checks(work)
    tasks = work / "openspec/changes/publication/tasks.md"
    tasks.write_text(tasks.read_text().replace("[ ]", "[x]"))
    commit_fixture(work, "feat: finish local publication")
    source_head = git(work, "rev-parse", "HEAD")
    run_ethos("prove", "--full", "--execute", "--expect-head", source_head, "--json", cwd=work)
    archived = archive_change(root=work, change="publication", expect_head=source_head, apply=True)
    assert archived["verdict"] == "pass", archived
    head = git(work, "rev-parse", "HEAD")
    assert openspec_governance_report(work, lifecycle=True)["change"] == "publication"
    run_ethos("prove", "--full", "--execute", "--expect-head", head, "--json", cwd=work)
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
        proven = run_ethos(
            "prove",
            *arguments,
            "--full",
            "--execute",
            "--expect-head",
            head,
            "--json",
            cwd=next_lane,
        )
        assert proven["verdict"] == "pass", proven
        assert proven["data"]["attestation"]["subject"] == f"git:commit:{head}"
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
