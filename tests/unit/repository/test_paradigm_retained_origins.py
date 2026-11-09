"""A verified retained original is not an authored document; anything less keeps every rule."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.adapters.mutation.paradigm_repair import repair_paradigm
from ethos.adapters.repo.content.observation import observed_document_origins
from ethos.repository.paradigm.report import repository_paradigm_report
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path

_FRONT = (
    "---\nsubject: sample:{subject}\nrole: {role}\nstate: canonical\nrelations: {{}}\n"
    "---\n\n# {title}\n\nPurpose: select the current owner.\n"
)
_AUTHORED = ("repository_paradigm_front_matter", "repository_paradigm_decision_record")
_NAMES = "repository_paradigm_authored_name"


def _repository(tmp_path: Path, original: str, text: str) -> Path:
    """Commit one original, then declare it retained in the docs taxonomy."""
    root = init_git_repo(tmp_path / "repo")
    path = root / original
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    revision = commit_fixture(root, "capture original observation")
    docs = root / "docs"
    (docs / "owner.md").write_text(
        _FRONT.format(subject="owner", role="reference", title="Owner"), encoding="utf-8"
    )
    (docs / "README.md").write_text(
        _FRONT.format(subject="docs", role="index", title="Docs")
        + "\nStart with [Owner](owner.md).\n",
        encoding="utf-8",
    )
    metadata = docs / "_meta"
    metadata.mkdir(exist_ok=True)
    (metadata / "README.md").write_text(
        _FRONT.format(subject="metadata", role="index", title="Metadata")
        + "\nRead [Taxonomy](taxonomy.toml).\n",
        encoding="utf-8",
    )
    (metadata / "taxonomy.toml").write_text(
        f'[[retained]]\npath = "{original}"\nsubject = "sample:observation"\n'
        f'role = "history"\nstate = "archived"\norigin = "{revision}:{original}"\n'
        'relations = { current_owner = "sample:owner" }\nreview_date = "2026-10-15"\n'
        'exit_condition = "Release after the current owner no longer needs this original."\n',
        encoding="utf-8",
    )
    git(root, "add", "--", "docs")
    return root


def _gaps(root: Path, *, observed: bool = True) -> list[str]:
    tracked = tuple(git(root, "ls-files").splitlines())
    origins = observed_document_origins(root) if observed else None
    report = repository_paradigm_report(
        root, tracked_paths=tracked, line_endings=None, retained_origins=origins
    )
    return [str(gap) for gap in report["required_gaps"]]


@pytest.mark.parametrize(
    "original",
    ["docs/history/observation.md", "docs/history/ADR-0003 Old Choice.md", "docs/Old_Notes/a.md"],
    ids=["plain", "decision-record-name", "non-kebab-directory"],
)
def test_a_verified_original_is_not_an_authored_document(tmp_path: Path, original: str) -> None:
    """No front-matter, decision-record or authored-name gap names a verified original."""
    root = _repository(tmp_path, original, "# Original\n\nObserved record.\n")
    named = [gap for gap in _gaps(root) if original in gap or "Old_Notes" in gap]
    assert named == []


@pytest.mark.parametrize("change", ["bytes", "mode", "unobserved", "malformed"])
def test_an_original_that_does_not_verify_keeps_every_rule(tmp_path: Path, change: str) -> None:
    """A changed, mode-mismatched, unobserved or malformed original is judged as authored."""
    original = "docs/history/observation.md"
    root = _repository(tmp_path, original, "# Original\n\nObserved record.\n")
    path = root / original
    if change == "bytes":
        path.write_text(path.read_text(encoding="utf-8") + "Changed.\n", encoding="utf-8")
    elif change == "mode":
        path.chmod(0o755)
    elif change == "malformed":
        (root / "docs/_meta/taxonomy.toml").write_text("[[retained]\n", encoding="utf-8")
    gaps = _gaps(root, observed=change != "unobserved")
    assert f"{_AUTHORED[0]}:{original}" in gaps


def test_an_ordinary_document_without_front_matter_still_fails(tmp_path: Path) -> None:
    """A tracked document under the docs root that no taxonomy declares keeps its gap."""
    root = _repository(tmp_path, "docs/history/observation.md", "# Original\n\nObserved.\n")
    (root / "docs/notes.md").write_text("# Notes\n\nNo front matter.\n", encoding="utf-8")
    git(root, "add", "--", "docs/notes.md")
    assert f"{_AUTHORED[0]}:docs/notes.md" in _gaps(root)


@pytest.mark.parametrize("case", ["verified", "changed"])
def test_the_repair_plans_no_edit_of_a_verified_original(tmp_path: Path, case: str) -> None:
    """A wrapped front matter is history in a verified original, and an edit elsewhere."""
    original = "docs/history/observation.md"
    root = _repository(tmp_path, original, "<!--\n---\nsubject: sample:old\n---\n-->\n\n# Old\n")
    if case == "changed":
        path = root / original
        path.write_text(path.read_text(encoding="utf-8") + "Changed.\n", encoding="utf-8")
    edited = [str(edit["path"]) for edit in repair_paradigm(root=root)["edits"]]
    assert (original in edited) is (case == "changed")
