"""`[artifacts]` in `rules.toml` moves into the profile's record roots before the table retires."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

import pytest

from ethos.contracts.paradigm.declaration import load_repository_paradigm
from ethos.repository.paradigm.gap import tracked_text
from ethos.repository.paradigm.records import record_binding_gaps
from ethos.repository.paradigm.repair import RepairPlan
from ethos.repository.paradigm.repair import paradigm_repair_plan
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path

PROFILE, RULES = ".ethos/profile.toml", ".ethos/rules.toml"


def _repository(tmp_path: Path, roots: str) -> Path:
    repo = init_git_repo(tmp_path / "repo")
    (repo / ".ethos").mkdir(exist_ok=True)
    (repo / PROFILE).write_text('profile_id = "records"\n', encoding="utf-8")
    table = f"[artifacts]\nstate_tracked_truth = false\ndurable_evidence_roots = {roots}\n"
    (repo / RULES).write_text(table, encoding="utf-8")
    commit_fixture(repo, "declare the artifacts table")
    return repo


def _plan(repo: Path) -> RepairPlan:
    paradigm = load_repository_paradigm()
    tracked = frozenset(git(repo, "ls-files").splitlines())
    rules = tracked_text(repo, paradigm.binding.path("rules"), tracked)
    return paradigm_repair_plan(repo, record_binding_gaps(paradigm, repo, tracked, rules))


def test_the_roots_move_to_the_profile_before_the_table_retires(tmp_path: Path) -> None:
    """One repair declares the folded roots, the next retires the table, and a third is empty."""
    repo = _repository(tmp_path, '["evidence", "evidence/claims"]')
    rounds = []
    for _round in range(3):
        plan = _plan(repo)
        rounds.append([(edit.path, edit.after is None) for edit in plan.edits])
        for edit in plan.edits:
            if edit.after is None:
                (repo / edit.path).unlink()
            else:
                (repo / edit.path).write_text(edit.after, encoding="utf-8")

    assert rounds == [[(PROFILE, False)], [(RULES, True)], []]
    profile = tomllib.loads((repo / PROFILE).read_text(encoding="utf-8"))
    assert profile == {"profile_id": "records", "record_roots": ["evidence/"]}


@pytest.mark.parametrize("roots", ['["/abs"]', '["a/../b"]', '["a//b"]', "[1]", '"evidence"'])
def test_an_invalid_root_is_reported_and_never_repaired(tmp_path: Path, roots: str) -> None:
    """A root that is not a repository directory stays the author's to name; nothing is edited."""
    plan = _plan(_repository(tmp_path, roots))

    assert plan.edits == ()
    assert [gap.carrier for gap in plan.report_only] == [
        f"{RULES}:artifacts.durable_evidence_roots"
    ]
