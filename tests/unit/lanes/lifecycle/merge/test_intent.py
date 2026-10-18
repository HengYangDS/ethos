"""Native merge intent preserves prior contributions and exact incoming task disposition."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from ethos.adapters.admission.prewrite import prewrite_guard
from ethos.adapters.repo.git import run_git
from tests.support.ethos_cli_runner import run_ethos
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import create_change_source_lane
from tests.support.governed_repository import git
from tests.support.governed_repository import start_adopted_candidate
from tests.support.governed_repository import write_active_commitment
from tests.support.openspec_lifecycle import HOLDER
from tests.support.openspec_lifecycle import apply_merge
from tests.support.openspec_lifecycle import native_merge_fixture
from tests.support.openspec_lifecycle import preview_merge
from tests.support.runtime_scenarios import git_process


def test_explicit_merge_intent_preserves_unchanged_incoming_change(tmp_path, monkeypatch):
    """Explicit authoring scope does not adopt the other parent's unchanged intent."""
    work = native_merge_fixture(tmp_path)
    monkeypatch.setenv("ETHOS_CHANGE", "publication")
    (work / "README.md").write_text("# Accepted combined resolution\n")
    git(work, "add", "README.md")
    incoming = git(work, "rev-parse", "MERGE_HEAD")
    path = "openspec/changes/static-delivery/tasks.md"
    before = git(work, "show", f":{path}")
    assert before == git(work, "show", f"{incoming}:{path}")
    preview = preview_merge(work, "continue")
    assert preview["data"]["observation"]["parents"] == [incoming]
    assert git(work, "show", f":{path}") == before
    assert git(work, "rev-parse", "MERGE_HEAD") == incoming


def test_merge_intent_preserves_native_composition_of_prior_change(tmp_path, monkeypatch):
    """Earlier contributions from both parents are not new continuation authoring."""
    repo, candidate = start_adopted_candidate(tmp_path)
    write_active_commitment(candidate, change_id="shared")
    commit_fixture(candidate, "feat: declare shared intent")
    work = create_change_source_lane(
        repo,
        tmp_path / "work",
        change_id="publication",
        holder_ref=HOLDER,
        base_ref="candidate/dev",
    )
    path = "openspec/changes/shared/design.md"
    own = work / path
    own.write_text(own.read_text().replace("Test-only governed fixture.", "Local contribution."))
    (work / "README.md").write_text("# Local contribution\n")
    commit_fixture(work, "feat: extend local design")
    other = candidate / path
    other.write_text(other.read_text().replace("Run focused lifecycle tests.", "Incoming proof."))
    (candidate / "README.md").write_text("# Incoming contribution\n")
    incoming = commit_fixture(candidate, "feat: extend incoming proof")
    assert git_process(work, "merge", "--no-ff", "--no-commit", incoming).returncode == 1
    (work / "README.md").write_text("# Accepted combined resolution\n")
    git(work, "add", "README.md")
    before = git(work, "show", f":{path}")
    assert "Local contribution." in before
    assert "Incoming proof." in before
    monkeypatch.setenv("ETHOS_CHANGE", "publication")
    preview = preview_merge(work, "continue")
    assert preview["data"]["observation"]["parents"] == [incoming]
    assert git(work, "show", f":{path}") == before


@pytest.mark.parametrize("disposition", ["present", "absent"])
def test_merge_continue_preserves_exact_incoming_task_disposition(
    tmp_path, monkeypatch, disposition
):
    """Exact import or incoming deletion resolves a conflict without authoring progress."""
    repo, candidate = start_adopted_candidate(tmp_path)
    write_active_commitment(candidate, change_id="shared")
    commit_fixture(candidate, "feat: declare shared intent")
    work = create_change_source_lane(
        repo,
        tmp_path / "work",
        change_id="publication",
        holder_ref=HOLDER,
        base_ref="candidate/dev",
    )
    path = "openspec/changes/shared/tasks.md"
    own, other = work / path, candidate / path
    own.write_text(own.read_text().replace("fixture lifecycle", "local qualification"))
    (work / "README.md").write_text("# Local contribution\n")
    before = commit_fixture(work, "feat: extend local task")
    if disposition == "present":
        other.write_text(other.read_text().replace("fixture lifecycle", "incoming qualification"))
        imported = other.read_bytes()
    else:
        git(candidate, "rm", "-r", "--", "openspec/changes/shared")
        imported = None
    (candidate / "README.md").write_text("# Incoming contribution\n")
    incoming = commit_fixture(candidate, "feat: update incoming task disposition")
    assert git_process(work, "merge", "--no-ff", "--no-commit", incoming).returncode == 1
    assert path in git(work, "diff", "--name-only", "--diff-filter=U").splitlines()
    monkeypatch.setenv("ETHOS_CHANGE", "publication")
    if imported is None:
        own.unlink()
        own.parent.rmdir()
        conflicts = git(work, "ls-files", "-u")
        with TemporaryDirectory(dir=tmp_path) as temporary:
            environment = {"GIT_INDEX_FILE": str(Path(temporary) / "index")}
            run_git(work, "read-tree", "HEAD", env=environment)
            run_git(work, "add", "--all", env=environment)
            admission = prewrite_guard(
                root=work,
                paths=[Path(path)],
                editor_root=work,
                require_editor_root=True,
                staged=True,
                index_env=environment,
            )
            assert admission["verdict"] == "pass", admission["required_gaps"]
            assert admission["patch_admission"]["effects"][path] == "delete"
            assert git(work, "ls-files", "-u") == conflicts
        assert not Path(temporary).exists()
        git(work, "rm", "--", path)
    else:
        own.write_bytes(imported)
        git(work, "add", path)
    (work / "README.md").write_text("# Accepted combined resolution\n")
    git(work, "add", "README.md")
    result = apply_merge(work, preview_merge(work, "continue"))
    assert result["verdict"] == "pass", result
    assert git(work, "rev-list", "--parents", "-n", "1", "HEAD").split()[1:] == [before, incoming]
    if imported is None:
        assert not own.exists()
        assert git_process(work, "cat-file", "-e", f"HEAD:{path}").returncode != 0
    else:
        assert own.read_bytes() == imported
        assert git(work, "show", f"HEAD:{path}") == git(work, "show", f"{incoming}:{path}")


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
