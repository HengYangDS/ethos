from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.openspec.lifecycle.archive_transition as archive
from ethos.repository.profile import INVALID_PROFILE_ERROR

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


def test_archive_attestation_remains_current_for_descendant_head(monkeypatch, tmp_path) -> None:
    desired = "c" * 40
    current = "d" * 40

    def run_git(_root: Path, *args: str, **_kwargs: object) -> SimpleNamespace:
        if args[:3] == ("merge-base", "--is-ancestor", desired):
            return SimpleNamespace(returncode=0, stdout="")
        if args == ("rev-list", "--count", f"{desired}..{current}"):
            return SimpleNamespace(returncode=0, stdout="2\n")
        return SimpleNamespace(returncode=1, stdout="")

    plan = SimpleNamespace(
        policy={"transition": "openspec.archive", "change": CHANGE, "branch": "work/change"},
        commitment={"schema_version": 3, "id": f"change:{CHANGE}", "acceptance": ["done"]},
        facts={"values": {"changed_paths": [f"{ARCHIVE}/tasks.md"]}},
        digest="plan",
    )
    effect = SimpleNamespace(
        updates={
            "refs/heads/work/change": SimpleNamespace(desired=desired),
        }
    )
    attestation = SimpleNamespace(
        predicate="effect:git-ref-update",
        verifier="agent:test",
        id="attestation",
        effect_digest="effect",
    )
    monkeypatch.setattr(archive, "read_attestation_set", lambda _root: ({}, [attestation]))
    monkeypatch.setattr(archive, "plan_from_attestation", lambda _attestation: plan)
    monkeypatch.setattr(archive, "git_effect_from_plan", lambda _plan: effect)
    monkeypatch.setattr(archive, "validate_git_effect_attestation", lambda *_a, **_k: None)
    monkeypatch.setattr(
        archive, "current_tree", lambda _root, commit: "tree" if commit == desired else ""
    )
    monkeypatch.setattr(archive, "run_git", run_git)

    recovered = archive.attested_archive_transition(tmp_path, head=current)

    assert recovered is not None
    commitment, authority = recovered
    assert commitment.id == f"change:{CHANGE}"
    assert authority["attestation_id"] == "attestation"


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
