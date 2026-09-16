"""Native parent provenance distinguishes coexisting official Change intent."""

from pathlib import Path

import pytest

from ethos.adapters.mutation.lane_lifecycle.archive.command import archive_change
from ethos.adapters.openspec.commitment import load_openspec_commitment
from ethos.adapters.openspec.governance import openspec_governance_report
from tests.support.ethos_cli_runner import run_ethos
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import write_active_commitment
from tests.support.openspec_lifecycle import native_merge_fixture


@pytest.fixture
def pending_merge(tmp_path: Path) -> Path:
    """Reproduce independent open Changes with a real unresolved native merge."""
    return native_merge_fixture(tmp_path)


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
