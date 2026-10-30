"""Check archive relocation, its scope and its isolated postimage."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.openspec.lifecycle.archive_transition as archive
from ethos.repository.profile import INVALID_PROFILE_ERROR
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_repo_with_candidate

if TYPE_CHECKING:
    from pathlib import Path


HEAD = "a" * 40
TREE = "b" * 40
CHANGE = "change"
ACTIVE = "openspec/changes/change"
ARCHIVE = "openspec/changes/archive/2026-08-10-change"
SOURCE_ARTIFACTS = (
    f"{ACTIVE}/.openspec.yaml",
    f"{ACTIVE}/proposal.md",
    f"{ACTIVE}/design.md",
    f"{ACTIVE}/tasks.md",
    f"{ACTIVE}/specs/contracts/spec.md",
)


def _profile(*, valid: bool = True) -> SimpleNamespace:
    if not valid:
        return SimpleNamespace(state="invalid", declaration=None)
    return SimpleNamespace(
        state="valid",
        declaration=SimpleNamespace(openspec=SimpleNamespace(material_paths=("openspec/**",))),
    )


def _git(
    monkeypatch: pytest.MonkeyPatch,
    *,
    collision: bool = False,
    preserved: bool = True,
) -> None:
    source_tree = "source-tree"
    prior_tree = "prior-tree" if collision else ""
    preservation = archive.collision_preservation_path(ARCHIVE, prior_tree, HEAD)

    def run_git(_root: Path, *args: str, **_kwargs: object) -> SimpleNamespace:
        if args[:3] == ("ls-tree", "-r", "--name-only"):
            return SimpleNamespace(returncode=0, stdout="\n".join(SOURCE_ARTIFACTS))
        if args[0] != "rev-parse":
            return SimpleNamespace(returncode=1, stdout="")
        value = {
            f"{HEAD}:{ACTIVE}": source_tree,
            f"{TREE}:{ARCHIVE}": source_tree,
            f"{HEAD}:{ARCHIVE}": prior_tree,
            f"{TREE}:{preservation}": prior_tree if preserved else "wrong",
        }.get(args[1], "")
        return SimpleNamespace(returncode=0 if value else 1, stdout=value)

    monkeypatch.setattr(archive, "run_git", run_git)
    monkeypatch.setattr(archive, "archive_projection_scope", lambda *_args, **_kwargs: ((), ()))


def _scope(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    changed_paths: tuple[str, ...],
    collision: bool = False,
    preserved: bool = True,
) -> dict[str, object] | None:
    _git(monkeypatch, collision=collision, preserved=preserved)
    monkeypatch.setattr(archive, "load_repository_profile", lambda _root: _profile())
    return archive.archive_postimage_scope_report(
        tmp_path,
        changed_paths=changed_paths,
        requested_change=CHANGE,
        tree=TREE,
        source_head=HEAD,
    )


def test_archive_scope_accepts_only_exact_official_change_relocation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    moved = tuple(path.replace(ACTIVE, ARCHIVE, 1) for path in SOURCE_ARTIFACTS)
    report = _scope(monkeypatch, tmp_path, changed_paths=moved)

    assert report is not None
    assert report["verdict"] == "pass"
    assert report["archive_path"] == ARCHIVE
    assert report["changes"] == [{"name": CHANGE, "path": ARCHIVE}]
    assert report["uncovered_paths"] == []

    retired = _scope(
        monkeypatch,
        tmp_path,
        changed_paths=(f"{ARCHIVE}/extra.txt",),
    )
    assert retired is not None
    assert retired["verdict"] == "block"
    assert _scope(monkeypatch, tmp_path, changed_paths=(f"{ARCHIVE}/tasks.md", "README.md")) is None


def test_archive_scope_maps_only_proven_delta_specs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    report = _scope(
        monkeypatch,
        tmp_path,
        changed_paths=(
            f"{ARCHIVE}/tasks.md",
            "openspec/specs/contracts/spec.md",
            "openspec/specs/unproven/spec.md",
        ),
    )

    assert report is not None
    assert report["covered_paths"] == [
        {"path": f"{ARCHIVE}/tasks.md", "changes": [CHANGE]},
        {"path": "openspec/specs/contracts/spec.md", "changes": [CHANGE]},
    ]
    assert report["uncovered_paths"] == ["openspec/specs/unproven/spec.md"]


def test_archive_scope_requires_exact_collision_preservation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    moved = tuple(path.replace(ACTIVE, ARCHIVE, 1) for path in SOURCE_ARTIFACTS)
    assert (
        _scope(
            monkeypatch,
            tmp_path,
            changed_paths=moved,
            collision=True,
            preserved=False,
        )
        is None
    )

    report = _scope(
        monkeypatch,
        tmp_path,
        changed_paths=moved,
        collision=True,
        preserved=True,
    )
    assert report is not None
    assert str(report["preserved_archive_path"]).startswith(f"{ARCHIVE}-")


def test_committed_archive_scope_is_inferred_without_a_lease_or_carrier(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    moved = tuple(path.replace(ACTIVE, ARCHIVE, 1) for path in SOURCE_ARTIFACTS)
    _git(monkeypatch)
    monkeypatch.setattr(archive, "load_repository_profile", lambda _root: _profile())
    monkeypatch.setattr(archive, "current_tree", lambda *_args: TREE)

    def git_stdout(_root: Path, *args: str) -> str:
        return {
            ("rev-parse", "HEAD"): "c" * 40,
            ("rev-parse", f"{'c' * 40}^"): HEAD,
        }.get(args, "")

    monkeypatch.setattr(archive, "git_stdout", git_stdout)
    report = archive.lease_bound_archive_scope_report(
        tmp_path,
        changed_paths=moved,
    )

    assert report is not None
    assert report["verdict"] == "pass"
    assert report["state"] == "post_archive_closeout"
    assert report["changes"] == [{"name": CHANGE, "path": ARCHIVE}]


def test_archive_scope_rejects_invalid_profile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    moved = tuple(path.replace(ACTIVE, ARCHIVE, 1) for path in SOURCE_ARTIFACTS)
    _git(monkeypatch)
    monkeypatch.setattr(archive, "load_repository_profile", lambda _root: _profile(valid=False))

    with pytest.raises(ValueError, match=INVALID_PROFILE_ERROR):
        archive.archive_postimage_scope_report(
            tmp_path,
            changed_paths=moved,
            requested_change=CHANGE,
            tree=TREE,
            source_head=HEAD,
        )


@pytest.fixture
def native_archive(tmp_path):
    """Provide real Git objects, not an official CLI execution claim."""
    repo, _candidate = init_repo_with_candidate(tmp_path)
    for relative in SOURCE_ARTIFACTS:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"source artifact: {relative}\n")
    head = commit_fixture(repo, "declare archive source")
    return repo, head


@pytest.mark.parametrize(
    "mode", ["unchanged", "move", "retained_active", "foreign", "missing_change"]
)
def test_archive_postimage_uses_isolated_native_git_projection(native_archive, mode):
    repo, head = native_archive
    index = (repo / ".git/index").read_bytes()
    target = repo / ARCHIVE
    if mode not in {"unchanged", "missing_change"}:
        target.parent.mkdir(parents=True)
        (repo / ACTIVE).rename(target)
        if mode == "retained_active":
            (repo / ACTIVE).mkdir()
            (repo / ACTIVE / "tasks.md").write_text("not fully archived\n")
        elif mode == "foreign":
            (repo / "foreign.txt").write_text("unrelated\n")
    before = git(repo, "status", "--porcelain")
    report = archive.archive_postimage(
        repo, head=head, change="" if mode == "missing_change" else CHANGE
    )
    assert (repo / ".git/index").read_bytes() == index
    assert git(repo, "rev-parse", "HEAD") == head
    assert git(repo, "status", "--porcelain") == before
    if mode == "missing_change":
        assert report is None
        return
    assert report is not None
    assert report.active_present is (mode in {"unchanged", "retained_active"})
    if mode == "move":
        assert report.scope is not None
        assert report.scope["verdict"] == "pass"
        assert report.scope["archive_path"] == ARCHIVE
        assert report.scope["completion_artifacts"] == sorted(SOURCE_ARTIFACTS)
    else:
        assert report.scope is None


@pytest.mark.parametrize(
    "mode",
    [
        "inferred",
        "selected",
        "wrong_change",
        "preservation_mismatch",
        "nonarchive",
        "missing_parent",
        "missing_source",
    ],
)
def test_committed_archive_selection_binds_current_git_diff(native_archive, monkeypatch, mode):
    repo, head = native_archive
    target = repo / ARCHIVE
    target.parent.mkdir(parents=True)
    (repo / ACTIVE).rename(target)
    commit_fixture(repo, "archive exact source")
    if mode == "missing_parent":
        native = archive.git_stdout
        monkeypatch.setattr(
            archive,
            "git_stdout",
            lambda root, *args: "" if args[-1].endswith("^") else native(root, *args),
        )
    elif mode == "missing_source":
        native = archive.run_git

        def run(root, *args, **kwargs):
            return (
                SimpleNamespace(returncode=1, stdout="")
                if args == ("rev-parse", f"{head}:{ACTIVE}")
                else native(root, *args, **kwargs)
            )

        monkeypatch.setattr(archive, "run_git", run)
    result = archive.lease_bound_archive_scope_report(
        repo,
        requested_change=CHANGE
        if mode == "selected"
        else "another"
        if mode == "wrong_change"
        else None,
        preserved_archive=(ARCHIVE, ARCHIVE + "-unbound")
        if mode == "preservation_mismatch"
        else None,
        changed_paths=("README.md",) if mode == "nonarchive" else (),
    )
    if mode in {"inferred", "selected"}:
        assert result is not None
        assert result["verdict"] == "pass"
        assert result["state"] == "post_archive_closeout"
        assert result["changes"] == [{"name": CHANGE, "path": ARCHIVE}]
    else:
        assert result is None


def test_archive_scope_requires_complete_source_enumeration(tmp_path, monkeypatch):
    _git(monkeypatch)
    native = archive.run_git

    def run(root, *args, **kwargs):
        return (
            SimpleNamespace(returncode=1, stdout="")
            if args[0] == "ls-tree"
            else native(root, *args, **kwargs)
        )

    monkeypatch.setattr(archive, "run_git", run)
    assert (
        archive.archive_postimage_scope_report(
            tmp_path,
            changed_paths=(f"{ARCHIVE}/tasks.md",),
            requested_change=CHANGE,
            tree=TREE,
            source_head=HEAD,
        )
        is None
    )
