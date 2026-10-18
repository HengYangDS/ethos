"""Read-only native merge admission preserves content and names the next legal action."""

import shlex
from pathlib import Path

import pytest

import ethos.adapters.repo.merge.effect as merge_effect
from tests.support.ethos_cli_runner import run_ethos
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.openspec_lifecycle import native_merge_fixture


def test_merge_start_cannot_overwrite_ignored_local_content(tmp_path):
    """An ignored path is not permission for Git's merge checkout to overwrite it."""
    work = native_merge_fixture(tmp_path, pending=False)
    candidate = next(
        Path(row.split(" ", 1)[1])
        for row in git(work, "worktree", "list", "--porcelain").splitlines()
        if row.startswith("worktree ")
        and Path(row.split(" ", 1)[1]).name != "work"
        and git(Path(row.split(" ", 1)[1]), "branch", "--show-current") == "candidate/dev"
    )
    (candidate / "personal-cache.bin").write_bytes(b"incoming tracked data\n")
    commit_fixture(candidate, "feat: add incoming tracked data")
    exclude = Path(git(work, "rev-parse", "--path-format=absolute", "--git-path", "info/exclude"))
    exclude.parent.mkdir(exist_ok=True)
    with exclude.open("a") as stream:
        stream.write("\npersonal-cache.bin\n")
    local = work / "personal-cache.bin"
    local.write_bytes(b"valuable ignored local data\n")
    preview = run_ethos(
        "lane", "refresh-base", "--strategy", "merge", "--mode", "start", "--json", cwd=work
    )
    assert preview["required_gaps"] == ["merge_ignored_content_collision:personal-cache.bin"]
    assert local.read_bytes() == b"valuable ignored local data\n"


def test_default_refresh_routes_pending_merge_to_its_owner(tmp_path):
    """A pending native merge cannot be treated as an ordinary dirty rebase."""
    work = native_merge_fixture(tmp_path)
    report = run_ethos("lane", "refresh-base", "--json", cwd=work)
    assert "merge_in_progress" in report["required_gaps"], report
    assert report["next_action"].startswith("ethos lane refresh-base --strategy merge")


def test_merge_continue_cannot_claim_incoming_task_completion(tmp_path):
    """A selected local Change does not own edits to the other parent's task state."""
    work = native_merge_fixture(tmp_path)
    (work / "README.md").write_text("# Local resolution\n")
    incoming = work / "openspec/changes/static-delivery/tasks.md"
    incoming.write_text(incoming.read_text().replace("[ ]", "[x]"))
    git(work, "add", "README.md", str(incoming))
    before = git(work, "rev-parse", "HEAD")
    report = run_ethos(
        "lane", "refresh-base", "--strategy", "merge", "--mode", "continue", "--json", cwd=work
    )
    assert report["verdict"] == "block", report
    assert any("incoming_change_modified" in gap for gap in report["required_gaps"])
    assert git(work, "rev-parse", "HEAD") == before


@pytest.mark.parametrize(
    "case", ["unresolved", "unstaged", "autostash", "competing", "multi-parent"]
)
def test_native_unsupported_state_rejects_continue_without_side_effect(tmp_path, case):
    """Unsupported native protocols are explicit boundaries, not optimistic execution."""
    work = native_merge_fixture(tmp_path)
    if case == "unstaged":
        (work / "README.md").write_text("staged resolution\n")
        git(work, "add", "README.md")
        (work / "README.md").write_text("later unaccepted resolution\n")
    elif case == "autostash":
        merge_effect.git_path(work, "MERGE_AUTOSTASH").write_text(git(work, "rev-parse", "HEAD"))
    elif case == "competing":
        merge_effect.git_path(work, "CHERRY_PICK_HEAD").write_text(git(work, "rev-parse", "HEAD"))
    elif case == "multi-parent":
        parent_file = merge_effect.git_path(work, "MERGE_HEAD")
        parent_file.write_text(parent_file.read_text() + git(work, "rev-parse", "HEAD") + "\n")
    before = git(work, "rev-parse", "HEAD"), git(work, "ls-files", "--stage")
    report = run_ethos(
        "lane", "refresh-base", "--strategy", "merge", "--mode", "continue", "--json", cwd=work
    )
    expected = {
        "unresolved": "merge_unresolved_index",
        "unstaged": "merge_unstaged_resolution",
        "autostash": "merge_autostash_recovery_unsupported",
        "competing": "merge_competing_native_operation",
        "multi-parent": "merge_multiple_parents_unsupported",
    }
    assert report["required_gaps"] == [expected[case]], report
    assert (git(work, "rev-parse", "HEAD"), git(work, "ls-files", "--stage")) == before


def test_conflicted_inspection_selects_exact_prewrite_not_a_status_loop(tmp_path):
    work = native_merge_fixture(tmp_path)
    report = run_ethos("lane", "refresh-base", "--strategy", "merge", "--json", cwd=work)
    assert report["required_gaps"] == ["merge_unresolved_index"]
    assert shlex.split(report["next_action"])[:4] == ["ethos", "lane", "prewrite", "README.md"]
    assert report["data"]["observation"]["conflicts"] == ["README.md"]
