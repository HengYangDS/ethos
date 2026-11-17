"""Native quality inputs refuse unreadable owners and linked configuration instead of guessing."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import pytest

import ethos.adapters.gates.native.inputs as native_inputs
import ethos.adapters.gates.tool as gate_tool
import ethos.adapters.repo.git_attributes as git_attributes
from ethos.adapters.repo.worktree_postimage import observe_execution_source
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_tree

_NOTE, _LICENSE = "docs/notes.md", "vendor/font/LICENSE"
# What the Git directory holds and no commit carries: one mark given and one taken back.
_LOCAL = f"{_NOTE} linguist-generated\n{_LICENSE} -linguist-vendored\n"
# Of these Git makes its own `HEAD`; a template would add hooks and `info`, where the
# exclude file and the attributes file of a Git directory live.
_TEMPLATE_ENTRIES = {"HEAD", "hooks", "info"}


@pytest.mark.parametrize("owner", [".ethos/profile.toml", "docs/_meta/taxonomy.toml"])
def test_authored_inputs_refuse_an_unreadable_owner(tmp_path, owner) -> None:
    """An unreadable profile or document taxonomy stops selection instead of guessing owners."""
    (tmp_path / owner).parent.mkdir(parents=True)
    (tmp_path / owner).write_text("[unterminated\n")
    with pytest.raises(ValueError, match=f"_invalid:{owner}$"):
        native_inputs.authored_source_files(tmp_path, paths=("README.md",))


def test_a_linked_tool_configuration_is_refused(tmp_path) -> None:
    """A repository configuration that links outside the root is refused, never followed."""
    repo = init_git_repo(tmp_path / "adopter")
    (repo / ".config/checks/taplo/taplo.toml").unlink()
    (repo / ".config/checks/taplo/taplo.toml").symlink_to(tmp_path / "taplo.toml")
    with pytest.raises(ValueError, match=r"^native_tool_configuration_invalid:taplo$"):
        native_inputs.native_configurations(repo, "taplo", ".config/checks/taplo/taplo.toml")


def test_a_moved_tool_configuration_selects_its_live_carrier(tmp_path) -> None:
    """A carrier deleted from the worktree but still indexed is absent; the live one binds."""
    repo = init_git_repo(tmp_path / "adopter")
    legacy = repo / ".config/checks/toml/taplo.toml"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("", encoding="utf-8")
    git(repo, "add", "--", ".config/checks/toml/taplo.toml")
    legacy.unlink()
    selected = native_inputs.native_repository_configuration(repo, "taplo")
    assert selected == repo / ".config/checks/taplo/taplo.toml"


def test_two_live_tool_configurations_stay_ambiguous(tmp_path) -> None:
    """Two materialized carriers still compete, so the tool configuration is refused."""
    repo = init_git_repo(tmp_path / "adopter")
    legacy = repo / ".config/checks/toml/taplo.toml"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match=r"^native_tool_configuration_ambiguous:taplo$"):
        native_inputs.native_repository_configuration(repo, "taplo")


def test_a_tracked_file_deleted_in_the_worktree_is_not_candidate_input(tmp_path) -> None:
    """A deletion the lane has not staged is not input, so no authored-text refusal names it."""
    repo = init_git_repo(tmp_path / "adopter")
    gone = repo / "docs/gone.md"
    gone.parent.mkdir(parents=True, exist_ok=True)
    gone.write_text("# Gone\n", encoding="utf-8")
    git(repo, "add", "--", "docs/gone.md")
    gone.unlink()

    selected = native_inputs.quality_source_files(repo, "*.md")

    assert "docs/gone.md" not in selected
    assert not [
        gap for gap in native_inputs.authored_text_gaps(repo, selected) if "path_invalid" in gap
    ]


def _marked_repository(tmp_path: Path, marks: str = "") -> tuple[Path, Path]:
    """Commit a misspelled note beside a license under a tracked mark; locate the local marks."""
    repo = init_git_repo(tmp_path / "adopter")
    tracked = "* text=auto eol=lf\nvendor/** linguist-vendored\n" + marks
    write_tree(repo, {".gitattributes": tracked, _LICENSE: "Grant\n"})
    git(repo, "add", "--", ".gitattributes", _LICENSE)
    commit_fixture_file(repo, _NOTE, "# Notes\n\nThis sentense has a mispelled word.\n", "notes")
    local = Path(git(repo, "rev-parse", "--path-format=absolute", "--git-path", "info/attributes"))
    local.parent.mkdir(parents=True, exist_ok=True)
    return repo, local


@pytest.mark.parametrize(
    "route", ["git-directory", "hidden-worktree-file", "configured-file", "caller-overlay"]
)
def test_a_local_attributes_line_takes_no_document_out_of_the_prose_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, route: str
) -> None:
    """A committed misspelling blocks as committed, under a local mark and with it removed.

    Each time the spelling check names both misspellings of the note's third line. The mark
    lies in the Git directory's attributes file, in a `.gitattributes` beside the note that the
    Git directory's exclude file hides from Git's status, or in a file that
    `core.attributesFile` names in the repository's configuration or in the caller's overlay.
    """
    repo, local = _marked_repository(tmp_path)
    marks = _LOCAL
    if route == "hidden-worktree-file":
        with local.with_name("exclude").open("a", encoding="utf-8") as exclude:
            exclude.write("/docs/.gitattributes\n")
        local, marks = repo / "docs/.gitattributes", "notes.md linguist-generated\n"
    if route == "configured-file":
        local = tmp_path / "configured-attributes"
        git(repo, "config", "core.attributesFile", local.as_posix())
    if route == "caller-overlay":
        local = tmp_path / "overlay-attributes"
        # The overlay gains one entry after those the suite already holds.
        held = int(os.environ.get("GIT_CONFIG_COUNT", "0"))
        monkeypatch.setenv("GIT_CONFIG_COUNT", str(held + 1))
        monkeypatch.setenv(f"GIT_CONFIG_KEY_{held}", "core.attributesFile")
        monkeypatch.setenv(f"GIT_CONFIG_VALUE_{held}", local.as_posix())
    readings = [gate_tool.prose_report(repo)]
    local.write_text(marks, encoding="utf-8")
    readings.append(gate_tool.prose_report(repo))
    local.unlink()
    readings.append(gate_tool.prose_report(repo))
    judged = [
        (reading["verdict"], str(reading["native"][0]["stdout"]).count(f"{_NOTE}:3: "))
        for reading in readings
    ]
    assert judged == [("block", 2)] * 3


def test_the_authored_selection_reads_marks_from_the_worktree_files_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A tracked mark leaves a path out and a local one changes nothing.

    A linked worktree reads the same, and so does the reader for a root named relative to the
    caller's directory. The format gate's text validity check keeps Git's own reading, as the
    predecessor did.
    """
    repo, local = _marked_repository(tmp_path)
    linked, paths = tmp_path / "linked", (_NOTE, _LICENSE)
    git(repo, "worktree", "add", "--detach", linked.as_posix())
    assert native_inputs.authored_source_files(linked, paths=paths) == [_NOTE]
    local.write_text(_LOCAL, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert git_attributes.worktree_received_paths(Path(repo.name), paths) == {_LICENSE}
    for root in (repo, linked):
        assert native_inputs.authored_source_files(root, paths=paths) == [_NOTE]
        assert native_inputs.authored_text_files(root, paths) == (_LICENSE,)


@pytest.mark.parametrize(
    "rule",
    [("core.ignoreCase", "true"), ("core.ignoreCase", "false"), ("--unset", "core.ignoreCase")],
)
def test_a_pattern_in_another_case_marks_nothing_on_any_host(
    tmp_path: Path, rule: tuple[str, str]
) -> None:
    """The marks are read by exact case, whatever the repository's or the volume's case rule.

    Git's own reading follows that rule, so one commit would be judged on one host and left out
    on another.
    """
    repo, _local = _marked_repository(tmp_path, "DOCS/NOTES.md linguist-generated\n")
    git(repo, "config", "core.ignoreCase", "true")
    git(repo, "config", *rule)
    assert native_inputs.authored_source_files(repo, paths=(_NOTE,)) == [_NOTE]


@pytest.mark.parametrize(
    "state",
    [
        "flagged-edit",
        pytest.param(
            "linked-parent",
            marks=pytest.mark.skipif(os.name == "nt", reason="a link needs a privilege"),
        ),
    ],
)
def test_the_marks_are_those_of_the_tree_that_the_source_binding_sees(
    tmp_path: Path, state: str
) -> None:
    """An edit that Git's status hides counts, and the binding sees it; a link reads no file."""
    repo, _local = _marked_repository(tmp_path)
    commit_fixture_file(repo, "docs/.gitattributes", "# no mark\n", "an attributes file")
    head, mark = git(repo, "rev-parse", "HEAD"), "notes.md linguist-generated\n"
    tree = git(repo, "rev-parse", f"{head}^{{tree}}")
    if state == "flagged-edit":
        git(repo, "update-index", "--skip-worktree", "docs/.gitattributes")
        (repo / "docs/.gitattributes").write_text(mark, encoding="utf-8")
        assert git(repo, "status", "--porcelain") == ""
    else:
        write_tree(tmp_path / "outside", {".gitattributes": mark, "notes.md": "text\n"})
        shutil.rmtree(repo / "docs")
        (repo / "docs").symlink_to(tmp_path / "outside", target_is_directory=True)
    received = git_attributes.worktree_received_paths(repo, (_NOTE,))
    assert received == ({_NOTE} if state == "flagged-edit" else set())
    assert observe_execution_source(repo, head, tree)["worktree"] != tree


def test_a_refused_attribute_read_keeps_its_error_and_its_git_directory_is_removed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The reading's own Git directory is temporary, has no template and outlives no refusal."""
    repo, _local = _marked_repository(tmp_path)
    made: list[Path] = []
    native = git_attributes.run_git

    def refused(root: Path, *args: str, **options: Any) -> subprocess.CompletedProcess[Any]:
        if "check-attr" in args:
            made.append(Path(args[args.index("--git-dir") + 1]))
            assert made[0].parent.resolve() == Path(tempfile.gettempdir()).resolve()
            assert {entry.name for entry in made[0].iterdir()} & _TEMPLATE_ENTRIES == {"HEAD"}
            args = (*args[: args.index("check-attr") + 1], "--no-such-option")
        return native(root, *args, **options)

    monkeypatch.setattr(git_attributes, "run_git", refused)
    with pytest.raises(subprocess.CalledProcessError):
        native_inputs.authored_source_files(repo, paths=(_NOTE,))
    assert [directory.exists() for directory in made] == [False]
