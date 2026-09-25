"""Keep generated starter changes subordinate to authored Git history."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.adapters.repo.starter.evolution import compose_starter_evolution
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


def _history(
    tmp_path: Path, *, customize_template: bool, object_format: str = "sha1"
) -> tuple[Path, str, str]:
    repo = init_git_repo(tmp_path / "repo", object_format=object_format)
    (repo / "pyproject.toml").write_text('description = "old"\n', encoding="utf-8")
    (repo / "src").mkdir()
    (repo / "src/custom.py").write_text("value = 1\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "chore: generated baseline")
    baseline = git(repo, "rev-parse", "HEAD")
    if customize_template:
        (repo / "pyproject.toml").write_text('description = "authored"\n', encoding="utf-8")
    else:
        (repo / "src/custom.py").write_text("value = 2\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "feat: authored customization")
    return repo, baseline, git(repo, "rev-parse", "HEAD")


@pytest.mark.parametrize("object_format", ["sha1", "sha256"])
def test_starter_evolution_composes_disjoint_changes_without_source_effect(
    tmp_path: Path, object_format: str
) -> None:
    """Native object merge retains authored files and proposes only starter changes."""
    repo, baseline, current = _history(
        tmp_path, customize_template=False, object_format=object_format
    )
    refs = git(repo, "show-ref")

    report = compose_starter_evolution(
        repo,
        baseline=baseline,
        current=current,
        old_paths=("pyproject.toml",),
        new_files={"pyproject.toml": b'description = "new"\n'},
    )

    assert report["verdict"] == "pass"
    assert report["changed_paths"] == ["pyproject.toml"]
    assert '+description = "new"' in report["patch"]
    assert git(repo, "rev-parse", "HEAD") == current
    assert git(repo, "show-ref") == refs
    assert (repo / "src/custom.py").read_text(encoding="utf-8") == "value = 2\n"
    assert (repo / "pyproject.toml").read_text(encoding="utf-8") == 'description = "old"\n'


def test_starter_evolution_conflict_preserves_authored_bytes(tmp_path: Path) -> None:
    """An overlapping template change never writes markers into the adopter."""
    repo, baseline, current = _history(tmp_path, customize_template=True)
    before = (repo / "pyproject.toml").read_bytes()
    refs = git(repo, "show-ref")

    report = compose_starter_evolution(
        repo,
        baseline=baseline,
        current=current,
        old_paths=("pyproject.toml",),
        new_files={"pyproject.toml": b'description = "new"\n'},
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["starter_evolution_conflict"]
    assert report["patch"] == ""
    assert (repo / "pyproject.toml").read_bytes() == before
    assert git(repo, "rev-parse", "HEAD") == current
    assert git(repo, "show-ref") == refs


def test_starter_evolution_rejects_unreviewed_path_scope(tmp_path: Path) -> None:
    """Generated path traversal cannot become an object-store or filesystem effect."""
    repo, baseline, current = _history(tmp_path, customize_template=False)

    report = compose_starter_evolution(
        repo,
        baseline=baseline,
        current=current,
        old_paths=("pyproject.toml",),
        new_files={"../outside": b"unsafe"},
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["starter_evolution_path_unsafe"]
    assert not (tmp_path / "outside").exists()


def test_starter_evolution_rejects_linked_baseline_file(tmp_path: Path) -> None:
    """A claimed old generated file must be an actual regular Git blob."""
    repo = init_git_repo(tmp_path / "repo")
    target = repo / "pyproject.toml"
    try:
        target.symlink_to("../foreign.toml")
    except OSError:
        pytest.skip("file symlinks unavailable")
    git(repo, "add", "pyproject.toml")
    git(repo, "commit", "-m", "chore: linked baseline")
    head = git(repo, "rev-parse", "HEAD")

    report = compose_starter_evolution(
        repo,
        baseline=head,
        current=head,
        old_paths=("pyproject.toml",),
        new_files={"pyproject.toml": b'description = "new"\n'},
    )

    assert report["required_gaps"] == ["starter_evolution_baseline_paths_unsafe"]
    assert target.is_symlink()
