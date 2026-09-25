"""Keep generated starter changes subordinate to authored Git history."""

from __future__ import annotations

import hashlib
import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.lane_lifecycle.candidate_projection as candidate_projection
from ethos.adapters.mutation.lane_lifecycle.start import default_worktree_path
from ethos.adapters.repo.starter.evolution import compose_starter_evolution
from ethos.adapters.repo.starter.evolution import plan_starter_evolution
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.domain.adoption import adopt_repository
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import create_change_source_lane
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.runtime_scenarios import install_fixture_hook_runtime

if TYPE_CHECKING:
    from pathlib import Path


def _old_files() -> dict[str, str]:
    return {"pyproject.toml": hashlib.sha256(b'description = "old"\n').hexdigest()}


def _formed_python_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    target = tmp_path / "new-project"
    request = {
        "create": True,
        "purpose": "Old purpose.",
        "starter": "python-library",
        "author_name": "Test Contributor",
        "author_email": "test@example.invalid",
    }
    preview = adopt_repository(target, **request)
    assert preview.verdict == "pass"
    monkeypatch.setattr(
        candidate_projection, "install_hook_launchers", install_fixture_hook_runtime
    )
    applied = adopt_repository(
        target,
        **request,
        apply=True,
        authorize=True,
        expect_plan_digest=str(preview.data["plan_digest"]),
    )
    assert applied.verdict == "pass"
    git(target, "config", "user.name", "Test Contributor")
    git(target, "config", "user.email", "test@example.invalid")
    return target


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


def test_formed_starter_evolution_preserves_authored_customization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Recorded formation, not caller-selected paths, supplies old starter scope."""
    repo = _formed_python_repo(tmp_path, monkeypatch)
    custom = repo / "src" / "custom.py"
    custom.write_text("value = 1\n", encoding="utf-8")
    git(repo, "add", "src/custom.py")
    git(repo, "commit", "-m", "feat: customize project")
    current = git(repo, "rev-parse", "HEAD")
    refs = git(repo, "show-ref")

    report = plan_starter_evolution(repo, purpose="New purpose.")

    assert report["verdict"] == "pass"
    assert report["changed_paths"] == ["pyproject.toml"]
    assert "New purpose." in report["patch"]
    assert git(repo, "rev-parse", "HEAD") == current
    assert git(repo, "show-ref") == refs
    assert custom.read_text(encoding="utf-8") == "value = 1\n"


def test_formed_starter_evolution_reports_conflicting_authorship(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A recorded generator source does not authorize replacing an authored edit."""
    repo = _formed_python_repo(tmp_path, monkeypatch)
    pyproject = repo / "pyproject.toml"
    pyproject.write_text(pyproject.read_text().replace("Old purpose.", "Authored purpose."))
    git(repo, "add", "pyproject.toml")
    git(repo, "commit", "-m", "feat: customize project purpose")
    before = pyproject.read_bytes()

    report = plan_starter_evolution(repo, purpose="New purpose.")

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["starter_evolution_conflict"]
    assert pyproject.read_bytes() == before
    decision = adopt_repository(repo, evolve_starter=True, purpose="New purpose.")
    assert decision.user_decision_required is True


def test_starter_evolution_requires_formation_provenance(tmp_path: Path) -> None:
    """A normal authored repository cannot declare any path generated by assertion."""
    repo = init_git_repo(tmp_path / "unformed")

    report = plan_starter_evolution(repo, purpose="New purpose.")

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["starter_evolution_provenance_missing"]


def test_starter_evolution_uses_original_name_from_sibling_worktree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A Work Lane directory name cannot silently rename native generator output."""
    repo = _formed_python_repo(tmp_path, monkeypatch)
    candidate = default_worktree_path(repo, load_branch_role_policy(repo).candidate_branch)
    assert candidate.is_dir()

    report = plan_starter_evolution(candidate, purpose="New purpose.")

    assert report["verdict"] == "pass"
    assert report["changed_paths"] == ["pyproject.toml"]
    assert "src/new_project/__init__.py" in report["source_inputs"]["new_files_sha256"]


def test_starter_evolution_blocks_dirty_worktree_before_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A preview cannot imply that uncommitted authored bytes were merged."""
    repo = _formed_python_repo(tmp_path, monkeypatch)
    (repo / "notes.txt").write_text("authored and uncommitted\n", encoding="utf-8")

    report = plan_starter_evolution(repo, purpose="New purpose.")

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["starter_evolution_worktree_dirty"]
    assert (repo / "notes.txt").read_text(encoding="utf-8") == "authored and uncommitted\n"


def test_starter_evolution_public_preview_is_read_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Installed callers reach the same reviewable candidate without direct effects."""
    repo = _formed_python_repo(tmp_path, monkeypatch)
    before = git(repo, "rev-parse", "HEAD")
    refs = git(repo, "show-ref")

    result = run_ethos(
        "adopt",
        "--evolve-starter",
        "--purpose",
        "New purpose.",
        "--root",
        str(repo),
        "--json",
        cwd=repo,
    )

    assert result["verdict"] == "pass"
    assert result["data"]["changed_paths"] == ["pyproject.toml"]
    assert "New purpose." in result["data"]["patch"]
    assert git(repo, "rev-parse", "HEAD") == before
    assert git(repo, "show-ref") == refs


def test_starter_evolution_public_apply_refuses_generator_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A starter preview cannot become a repository write by adding --apply."""
    repo = _formed_python_repo(tmp_path, monkeypatch)
    before = (repo / "pyproject.toml").read_bytes()

    result = run_ethos_blocked(
        "adopt",
        "--evolve-starter",
        "--purpose",
        "New purpose.",
        "--root",
        str(repo),
        "--apply",
        "--authorize",
        "--json",
        cwd=repo,
    )

    assert result["required_gaps"] == ["starter_evolution_requires_work_lane"]
    assert (repo / "pyproject.toml").read_bytes() == before


def test_starter_evolution_reviewed_patch_uses_existing_lane_admission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An authored lane admits the exact reviewed patch, not a generator-owned write."""
    repo = _formed_python_repo(tmp_path, monkeypatch)
    actor = "agent:test:case:starter-upgrade"
    lane = create_change_source_lane(
        repo,
        tmp_path / "starter-upgrade-lane",
        branch="work/starter-upgrade",
        holder_ref=actor,
        base_ref=load_branch_role_policy(repo).candidate_branch,
    )
    assert not (lane / "openspec/specs").exists()
    commit_fixture_file(lane, "src/custom.py", "value = 1\n", "feat: authored extension")
    authored = (lane / "src/custom.py").read_bytes()
    monkeypatch.setenv("ETHOS_ACTOR", actor)
    monkeypatch.setenv("ETHOS_CHANGE", "fixture-change")

    preview = run_ethos(
        "adopt",
        "--evolve-starter",
        "--purpose",
        "New purpose.",
        "--root",
        str(lane),
        "--json",
        cwd=lane,
    )
    assert preview["verdict"] == "pass"
    assert preview["data"]["changed_paths"] == ["pyproject.toml"]
    patch = str(preview["data"]["patch"])
    patch_path = tmp_path / "reviewed.patch"
    patch_path.write_text(patch, encoding="utf-8")
    before = git(lane, "rev-parse", "HEAD")

    admitted = run_ethos(
        "lane",
        "prewrite",
        "--paths",
        "pyproject.toml",
        "--patch",
        str(patch_path),
        "--editor-root",
        str(lane),
        "--require-editor-root",
        "--root",
        str(lane),
        "--json",
        cwd=lane,
    )
    assert admitted["verdict"] == "pass"
    assert admitted["data"]["patch_admission"]["paths"] == ["pyproject.toml"]
    assert admitted["data"]["request_binding"]["expected_state"]["head"] == before
    subprocess.run(
        ["git", "apply", "--whitespace=error-all", "-"],
        input=patch,
        text=True,
        cwd=lane,
        check=True,
        capture_output=True,
    )
    assert (lane / "src/custom.py").read_bytes() == authored
    assert "New purpose." in (lane / "pyproject.toml").read_text(encoding="utf-8")
    git(lane, "add", "pyproject.toml")
    git(lane, "commit", "-m", "chore: upgrade reviewed starter")
    assert git(lane, "status", "--porcelain") == ""
    stale = run_ethos_blocked(
        "lane",
        "prewrite",
        "--paths",
        "pyproject.toml",
        "--patch",
        str(patch_path),
        "--editor-root",
        str(lane),
        "--require-editor-root",
        "--root",
        str(lane),
        "--json",
        cwd=lane,
    )
    assert stale["data"]["patch_admission"]["reason"] == "prewrite_patch_preimage_mismatch"
