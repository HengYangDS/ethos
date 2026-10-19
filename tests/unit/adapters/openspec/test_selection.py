"""Incoming Change admission preserves the other parent's exact unchanged intent."""

from pathlib import Path

import pytest

from ethos.adapters.admission.prewrite import prewrite_guard
from ethos.adapters.openspec.selection import incoming_change_gaps
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.openspec_lifecycle import native_merge_fixture
from tests.support.runtime_scenarios import git_process


@pytest.fixture
def pending_merge(tmp_path: Path) -> Path:
    """Reproduce independent open Changes with a real unresolved native merge."""
    return native_merge_fixture(tmp_path)


@pytest.mark.parametrize(
    "mode", ["staged", "authoring", "changed-incoming", "working-copy", "alternate-index"]
)
def test_merge_admission_preserves_exact_incoming_change(pending_merge, monkeypatch, mode):
    """Only staged, unchanged incoming intent can cross the selected Change boundary."""
    work = pending_merge
    tasks = work / "openspec/changes/static-delivery/tasks.md"
    (work / "README.md").write_text("# Combined contribution\n")
    git(work, "add", "README.md")
    index_env = None
    if mode == "alternate-index":
        index = Path(git(work, "rev-parse", "--path-format=absolute", "--git-path", "index"))
        alternate = work.parent / "alternate-index"
        alternate.write_bytes(index.read_bytes())
        index_env = {"GIT_INDEX_FILE": str(alternate)}
    if mode in {"changed-incoming", "working-copy", "alternate-index"}:
        tasks.write_text(tasks.read_text().replace("[ ]", "[x]"))
        if mode != "working-copy":
            with monkeypatch.context() as selected:
                if index_env:
                    selected.setenv("GIT_INDEX_FILE", index_env["GIT_INDEX_FILE"])
                git(work, "add", str(tasks))
    monkeypatch.setenv("ETHOS_CHANGE", "publication")
    before = (git(work, "rev-parse", "HEAD"), git(work, "write-tree"), tasks.read_bytes())

    report = prewrite_guard(
        root=work,
        paths=[work / "README.md", tasks],
        editor_root=work,
        require_editor_root=True,
        staged=mode != "authoring",
        index_env=index_env,
    )

    assert report["verdict"] == ("pass" if mode in {"staged", "working-copy"} else "block"), report[
        "required_gaps"
    ]
    if report["verdict"] == "block":
        gaps = report["required_gaps"]
        assert isinstance(gaps, list)
        assert any(
            isinstance(gap, str) and gap.startswith("openspec_change_path_mismatch:")
            for gap in gaps
        )
    assert (git(work, "rev-parse", "HEAD"), git(work, "write-tree"), tasks.read_bytes()) == before


def test_incoming_guard_preserves_local_change_not_authored_by_peer(tmp_path):
    """An inherited peer tree cannot take ownership of a distinct local contribution."""
    work = init_git_repo(tmp_path / "repo")
    common = work / "openspec/changes/common/tasks.md"
    common.parent.mkdir(parents=True)
    common.write_text("- [ ] Common contribution\n")
    commit_fixture(work, "feat: declare common intent")
    git(work, "checkout", "-b", "incoming")
    peer = work / "openspec/changes/peer/tasks.md"
    peer.parent.mkdir(parents=True)
    peer.write_text("- [ ] Peer contribution\n")
    incoming = commit_fixture(work, "feat: declare peer intent")
    git(work, "checkout", "dev")
    common.write_text("- [x] Common contribution\n")
    commit_fixture(work, "feat: preserve local companion")
    assert git_process(work, "merge", "--no-ff", "--no-commit", incoming).returncode == 0
    before = git(work, "write-tree")
    assert incoming_change_gaps(work, "publication", incoming, ("README.md",)) == []
    assert common.read_text() == "- [x] Common contribution\n"
    assert peer.read_text() == "- [ ] Peer contribution\n"
    assert incoming_change_gaps(
        work, "publication", incoming, ("openspec/changes/common/tasks.md",)
    ) == ["openspec_incoming_change_modified:common"]
    assert git(work, "write-tree") == before
