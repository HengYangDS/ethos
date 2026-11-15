"""Declared record roots: gates judge every record file; the format repair keeps older ones."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.adapters.gates.tool as gate_tool
from ethos.adapters.gates.formatting import source_format_report
from ethos.adapters.mutation.source_format import format_source
from ethos.repository.profile import INVALID_PROFILE_ERROR
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import prepared_work_lane
from tests.support.governed_repository import write_test_profile
from tests.support.governed_repository import write_tree

if TYPE_CHECKING:
    from pathlib import Path

_DRIFT = "# Record\n\ntext   \n\n- one\n\n- two\n"
_ROOT = "docs/decisions/"
_DECLARED = 'record_roots = [\n  "docs/decisions/",\n]\n'
_ALL = ("changed", "new", "old")


def _records(*names: str) -> list[str]:
    return [f"{_ROOT}{name}.md" for name in names]


@pytest.mark.parametrize(
    ("shape", "named", "kept"),
    [
        ("local-branch", (), ("old",)),
        ("github-hosted", (), _ALL),
        ("gitlab-proposal", (), _ALL),
        ("local-branch", ("old",), ()),
    ],
    ids=["local-branch", "github-hosted", "gitlab-proposal", "named-record"],
)
def test_gates_judge_every_record_and_the_repair_keeps_older_ones(
    tmp_path: Path, shape: str, named: tuple[str, ...], kept: tuple[str, ...]
) -> None:
    """The verdict is the same in every checkout shape; only the repair reads the local base.

    A hosted checkout holds the accepted branch as a tracking ref of `origin`, or not at all, so
    its base is named `unresolved` and the repair keeps every record file. A named record is
    judged and repaired whatever the base, and an invalid profile keeps its own refusal.
    """
    root = init_git_repo(tmp_path / "repo")
    write_test_profile(root, record_roots=(_ROOT,))
    write_tree(root, dict.fromkeys(_records("changed", "old"), _DRIFT))
    accepted = commit_fixture(root, "docs: accept two records")
    git(root, "checkout", "-q", "-b", "work/records")
    write_tree(root, {f"{_ROOT}new.md": _DRIFT})
    commit_fixture(root, "docs: add a record")
    write_tree(root, {f"{_ROOT}changed.md": _DRIFT + "\nMore.\n"})
    if shape != "local-branch":
        git(root, "remote", "add", "origin", "peer.git")
        git(root, "checkout", "-q", "--detach")
        git(root, "branch", "-q", "-D", "dev", "work/records")
    if shape == "github-hosted":
        git(root, "update-ref", "refs/remotes/origin/dev", accepted)
    paths, judged, held = tuple(_records(*named)), _records(*(named or _ALL)), _records(*kept)
    base = "" if named else accepted if shape == "local-branch" else "unresolved"
    drift = [f"source_format_drift:{path}" for path in judged]

    gate = source_format_report(root, paths=paths)
    assert (gate["required_gaps"], gate["record_base"], gate["record_paths"]) == (drift, base, held)
    check = format_source(root, paths=paths, check=True)
    assert check["required_gaps"] == drift
    assert "record_paths" in check["next_action"]
    repaired = format_source(root, paths=paths)["changed_paths"]
    assert [path for path in repaired if path.startswith(_ROOT)] == sorted({*judged} - {*held})
    if not named:
        markdown, *_lint, spacing = gate_tool.markdown_lint_report(root)["native"]
        assert (markdown["record_base"], markdown["record_paths"]) == (base, held)
        assert spacing["required_gaps"] == [f"markdown_list_spacing:{path}:7" for path in judged]
    (root / ".ethos/profile.toml").write_text("record_roots = 1\n", encoding="utf-8")
    assert format_source(root, paths=paths)["required_gaps"] == [INVALID_PROFILE_ERROR]


def test_the_apply_rewrites_no_record_that_the_base_holds_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """In a Work Lane the apply writes the new and the changed record and leaves the older one."""
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    monkeypatch.setenv("ETHOS_CHANGE", "fixture-change")
    accepted = dict.fromkeys(_records("changed", "old"), _DRIFT)
    lane = prepared_work_lane(tmp_path, name="records", files=accepted).worktree
    profile = lane / ".ethos/profile.toml"
    profile.write_text(profile.read_text().replace("\n", f"\n{_DECLARED}", 1), encoding="utf-8")
    write_tree(lane, {f"{_ROOT}new.md": _DRIFT, f"{_ROOT}changed.md": _DRIFT + "\nMore.\n"})

    head = git(lane, "rev-parse", "HEAD")
    applied = format_source(lane, apply=True, authorize=True, expect_head=head)
    assert (applied["verdict"], applied["record_paths"]) == ("pass", _records("old")), applied
    assert (lane / _ROOT / "old.md").read_text() == _DRIFT
    assert _DRIFT not in {(lane / path).read_text() for path in _records("changed", "new")}
