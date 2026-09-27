"""Keep generated starter changes subordinate to authored Git history."""

from __future__ import annotations

import hashlib
import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.starter.evolution as evolution
from ethos.adapters.repo.starter.evolution import compose_starter_evolution
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


def _old_files() -> dict[str, str]:
    return {"pyproject.toml": hashlib.sha256(b'description = "old"\n').hexdigest()}


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


@pytest.mark.parametrize(
    ("defect", "gap"),
    [
        ("digest", "starter_evolution_baseline_digest_invalid"),
        ("stale-head", "starter_evolution_head_changed"),
        ("unrelated-base", "starter_evolution_baseline_not_ancestor"),
        ("missing-path", "starter_evolution_baseline_paths_missing"),
    ],
)
def test_starter_evolution_requires_exact_source_history(
    tmp_path: Path, defect: str, gap: str
) -> None:
    """A valid-looking output cannot use an altered digest, HEAD or Git ancestry."""
    repo, baseline, current = _history(tmp_path, customize_template=False)
    old_files = _old_files()
    if defect == "digest":
        old_files["pyproject.toml"] = "invalid"
    elif defect == "stale-head":
        current = baseline
    elif defect == "unrelated-base":
        baseline = git(repo, "commit-tree", git(repo, "rev-parse", "HEAD^{tree}"))
    else:
        old_files["src/missing.py"] = hashlib.sha256(b"missing\n").hexdigest()
    before = git(repo, "rev-parse", "HEAD")

    report = compose_starter_evolution(
        repo,
        baseline=baseline,
        current=current,
        old_files=old_files,
        new_files={"pyproject.toml": b'description = "new"\n'},
    )

    assert report["required_gaps"] == [gap]
    assert report["patch"] == ""
    assert git(repo, "rev-parse", "HEAD") == before


def test_starter_evolution_revalidates_head_after_object_merge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A concurrent HEAD move invalidates a generated patch before it is offered."""
    repo, baseline, current = _history(tmp_path, customize_template=False)
    original_run_git = evolution.run_git
    head_reads = 0

    def changed_head(root: Path, *args, **kwargs):
        nonlocal head_reads
        if args[:2] == ("rev-parse", "HEAD"):
            head_reads += 1
            if head_reads == 2:
                return subprocess.CompletedProcess(args, 0, stdout="0" * len(current), stderr="")
        return original_run_git(root, *args, **kwargs)

    monkeypatch.setattr(evolution, "run_git", changed_head)
    report = compose_starter_evolution(
        repo,
        baseline=baseline,
        current=current,
        old_files=_old_files(),
        new_files={"pyproject.toml": b'description = "new"\n'},
    )
    assert report["required_gaps"] == ["starter_evolution_head_changed"]
    assert git(repo, "rev-parse", "HEAD") == current


def test_starter_evolution_reports_unavailable_object_sandbox(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A native observation failure is unknown, never a reviewable patch."""
    repo, baseline, current = _history(tmp_path, customize_template=False)
    refs = git(repo, "show-ref")

    def unavailable(_root: Path):
        message = "object sandbox unavailable"
        raise OSError(message)

    monkeypatch.setattr(evolution, "isolated_git_objects", unavailable)
    report = compose_starter_evolution(
        repo,
        baseline=baseline,
        current=current,
        old_files=_old_files(),
        new_files={"pyproject.toml": b'description = "new"\n'},
    )
    assert report["verdict"] == "unknown"
    assert report["required_gaps"] == ["starter_evolution_observation_unknown"]
    assert report["patch"] == ""
    assert git(repo, "show-ref") == refs
    assert git(repo, "rev-parse", "HEAD") == current


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
        old_files=_old_files(),
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
        old_files=_old_files(),
        new_files={"pyproject.toml": b'description = "new"\n'},
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["starter_evolution_conflict"]
    assert report["patch"] == ""
    assert (repo / "pyproject.toml").read_bytes() == before
    assert git(repo, "rev-parse", "HEAD") == current
    assert git(repo, "show-ref") == refs


@pytest.mark.parametrize("object_format", ["sha1", "sha256"])
@pytest.mark.parametrize("state", ["unchanged", "authored"])
def test_starter_removal_preserves_authored_history(
    tmp_path: Path, object_format: str, state: str
) -> None:
    """Drop unchanged starter bytes, but reject deletion of authored edits."""
    repo, baseline, current = _history(
        tmp_path, customize_template=state == "unchanged", object_format=object_format
    )
    authored = (repo / "src/custom.py").read_bytes()
    old_files = _old_files() | {"src/custom.py": hashlib.sha256(b"value = 1\n").hexdigest()}

    report = compose_starter_evolution(
        repo,
        baseline=baseline,
        current=current,
        old_files=old_files,
        new_files={"pyproject.toml": b'description = "old"\n'},
    )

    if state == "authored":
        assert report["required_gaps"] == ["starter_evolution_conflict"]
    else:
        assert report["changed_paths"] == ["src/custom.py"]
        assert "-value = 1" in report["patch"]
    assert (repo / "src/custom.py").read_bytes() == authored
    assert git(repo, "rev-parse", "HEAD") == current


def test_starter_evolution_rejects_false_prior_output_digest(tmp_path: Path) -> None:
    """A claimed generated path cannot substitute unrelated authored bytes."""
    repo, baseline, current = _history(tmp_path, customize_template=False)
    before = (repo / "pyproject.toml").read_bytes()
    refs = git(repo, "show-ref")

    report = compose_starter_evolution(
        repo,
        baseline=baseline,
        current=current,
        old_files={"pyproject.toml": "0" * 64},
        new_files={"pyproject.toml": b'description = "new"\n'},
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["starter_evolution_baseline_content_mismatch"]
    assert (repo / "pyproject.toml").read_bytes() == before
    assert git(repo, "show-ref") == refs


def test_starter_evolution_rejects_unreviewed_path_scope(tmp_path: Path) -> None:
    """Generated path traversal cannot become an object-store or filesystem effect."""
    repo, baseline, current = _history(tmp_path, customize_template=False)

    report = compose_starter_evolution(
        repo,
        baseline=baseline,
        current=current,
        old_files=_old_files(),
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
        old_files={"pyproject.toml": "0" * 64},
        new_files={"pyproject.toml": b'description = "new"\n'},
    )

    assert report["required_gaps"] == ["starter_evolution_baseline_paths_unsafe"]
    assert target.is_symlink()
