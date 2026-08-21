from __future__ import annotations

import json
import os
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.openspec.lifecycle.archive_effect as effect
import ethos.adapters.openspec.lifecycle.archive_transition as archive
from ethos.repository.profile import INVALID_PROFILE_ERROR
from tests.support.semantic import commitment_fixture

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Commitment


HEAD = "a" * 40
TREE = "b" * 40
CARRIER = "openspec/changes/archive/2026-08-10-change/commitment.toml"
ACTIVE = "openspec/changes/change/commitment.toml"


def _commitment(*, change_identity: bool = True) -> Commitment:
    commitment = commitment_fixture(
        id="change:change",
        intent="Archive exact governed work.",
        subjects=("repository:test",),
        scope=("openspec/changes/change/**",),
    )
    return commitment if change_identity else commitment.model_copy(update={"id": "change"})


def _lease(**updates: object) -> dict[str, object]:
    lease: dict[str, object] = {
        "lease_state": "valid",
        "expected_head": HEAD,
        "base_commitment_digest": _commitment().digest(),
    }
    lease.update(updates)
    return lease


def _profile(*, valid: bool = True) -> SimpleNamespace:
    if not valid:
        return SimpleNamespace(state="invalid", declaration=None)
    openspec = SimpleNamespace(material_paths=("openspec/**",))
    return SimpleNamespace(
        state="valid",
        declaration=SimpleNamespace(openspec=openspec),
    )


def _scope_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    *,
    state: str,
    carrier: str = CARRIER,
) -> None:
    source = _commitment()
    monkeypatch.setattr(archive, "archive_context", lambda _root: (HEAD, _lease(), source))
    monkeypatch.setattr(
        archive,
        "archive_binding",
        lambda *_args, **_kwargs: (state, TREE, carrier),
    )
    monkeypatch.setattr(archive, "load_commitment", lambda *_args, **_kwargs: source)
    monkeypatch.setattr(
        archive,
        "active_commitments",
        lambda *_args: (carrier,) if state == "completion_transition" else (),
    )
    monkeypatch.setattr(archive, "load_repository_profile", lambda _root: _profile())


def _scope_report(
    root: Path,
    *,
    changed_paths: tuple[str, ...],
    preserved_archive: tuple[str, str] | None = None,
) -> dict[str, object] | None:
    return archive.lease_bound_archive_scope_report(
        root,
        changed_paths=changed_paths,
        official_change_complete=True,
        completion_artifacts=(ACTIVE,),
        preserved_archive=preserved_archive,
    )


def test_archive_scope_rejects_non_change_identity_and_invalid_archived_carrier(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        archive,
        "archive_context",
        lambda _root: (HEAD, _lease(), _commitment(change_identity=False)),
    )
    assert archive.lease_bound_archive_scope_report(tmp_path) is None

    monkeypatch.setattr(
        archive,
        "archive_context",
        lambda _root: (HEAD, _lease(), _commitment()),
    )
    monkeypatch.setattr(
        archive, "archive_binding", lambda *_args, **_kwargs: ("archive_transition", TREE, CARRIER)
    )
    monkeypatch.setattr(
        archive,
        "load_commitment",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("invalid archive")),
    )
    assert archive.lease_bound_archive_scope_report(tmp_path, official_change_complete=True) is None


def test_archive_transition_fields_require_valid_lease_and_exact_target(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(effect, "git_stdout", lambda *_args, **_kwargs: "work/feature")
    monkeypatch.setattr(effect, "leases_by_branch", lambda _root: {"work/feature": {}})
    assert effect.lease_bound_archive_transition_fields(tmp_path, target_head=HEAD) is None

    source = _commitment()
    target = {
        "base_commitment_path": CARRIER,
        "base_commitment_digest": source.digest(),
        "base_commitment_bytes_sha256": "bytes",
        "expected_head": HEAD,
        "expected_tree": TREE,
    }

    def git_stdout(_root: Path, *args: str) -> str:
        if args == ("branch", "--show-current"):
            return "work/feature"
        if args == ("diff", "--name-only", f"{HEAD}..{HEAD}"):
            return CARRIER
        return ""

    monkeypatch.setattr(effect, "git_stdout", git_stdout)
    monkeypatch.setattr(effect, "leases_by_branch", lambda _root: {"work/feature": _lease()})
    monkeypatch.setattr(effect, "load_lease_bound_commitment", lambda *_args, **_kwargs: source)
    monkeypatch.setattr(effect, "current_tree", lambda *_args: TREE)
    monkeypatch.setattr(
        effect,
        "run_git",
        lambda *_args, **_kwargs: SimpleNamespace(stdout=f"{TREE}\n", returncode=0),
    )
    monkeypatch.setattr(
        effect,
        "archive_postimage_scope_report",
        lambda *_args, **_kwargs: {
            "verdict": "pass",
            "archive_path": CARRIER.removesuffix("/commitment.toml"),
        },
    )
    monkeypatch.setattr(effect, "exact_commitment_fields", lambda *_args, **_kwargs: target)
    monkeypatch.setenv(
        "ETHOS_ARCHIVE_TRANSITION",
        effect.archive_transition_environment(
            tmp_path,
            change="change",
            head=HEAD,
            changed_paths=(CARRIER,),
            official_change_complete=True,
            completion_artifacts=("tasks.md",),
        )["ETHOS_ARCHIVE_TRANSITION"],
    )

    assert effect.lease_bound_archive_transition_fields(tmp_path, target_head=HEAD) == target
    monkeypatch.delenv("ETHOS_ARCHIVE_TRANSITION")
    assert effect.lease_bound_archive_transition_fields(tmp_path, target_head=HEAD) is None


def _prepared_effect_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[str, str]:
    holder = "agent:owner"
    branch = "work/feature"
    generation = _lease(
        holder_ref=holder,
        lane_ref=branch,
        lease_id="lease:archive",
        epoch=7,
    )
    monkeypatch.setattr(effect, "current_tracked_head", lambda _root: HEAD)
    monkeypatch.setattr(effect, "current_tree", lambda *_args: TREE)
    monkeypatch.setattr(
        effect,
        "run_git",
        lambda *_args, **_kwargs: SimpleNamespace(stdout=f"{TREE}\n", returncode=0),
    )
    monkeypatch.setattr(
        effect,
        "archive_context",
        lambda _root: (HEAD, generation, _commitment()),
    )
    monkeypatch.setattr(
        effect,
        "archive_postimage_scope_report",
        lambda *_args, **_kwargs: {"verdict": "pass"},
    )
    environment = effect.archive_transition_environment(
        tmp_path,
        change="change",
        head=HEAD,
        changed_paths=(CARRIER,),
        official_change_complete=True,
        completion_artifacts=("tasks.md",),
    )
    monkeypatch.setenv("ETHOS_ARCHIVE_TRANSITION", environment["ETHOS_ARCHIVE_TRANSITION"])
    return branch, holder


def test_prepared_archive_authority_rejects_actor_mismatch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    branch, holder = _prepared_effect_dependencies(monkeypatch, tmp_path)

    admitted = effect.archive_prewrite_authority(
        tmp_path,
        changed_paths=(CARRIER,),
        branch=branch,
        actor=holder,
    )
    rejected = effect.archive_prewrite_authority(
        tmp_path,
        changed_paths=(CARRIER,),
        branch=branch,
        actor="agent:other",
    )

    assert admitted is not None
    assert admitted["authority_kind"] == "prepared_effect"
    assert admitted["material_scope"] == {"verdict": "pass"}
    assert rejected is None


@pytest.mark.parametrize("tamper", ["effect_identity", "changed_paths"])
def test_prepared_archive_authority_rejects_envelope_drift(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    tamper: str,
) -> None:
    branch, holder = _prepared_effect_dependencies(monkeypatch, tmp_path)
    payload = json.loads(os.environ["ETHOS_ARCHIVE_TRANSITION"])
    payload[tamper] = "0" * 64 if tamper == "effect_identity" else [ACTIVE]
    monkeypatch.setenv("ETHOS_ARCHIVE_TRANSITION", json.dumps(payload))

    assert (
        effect.archive_prewrite_authority(
            tmp_path,
            changed_paths=(CARRIER,),
            branch=branch,
            actor=holder,
        )
        is None
    )


def test_prepared_archive_ref_authority_rejects_wrong_parent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    desired = "c" * 40
    monkeypatch.setattr(
        effect,
        "git_stdout",
        lambda *_args, **_kwargs: f"{desired} {'d' * 40}",
    )

    assert (
        effect.prepared_archive_ref_authority(
            tmp_path,
            branch="work/feature",
            old_value=HEAD,
            new_value=desired,
            actor="agent:owner",
        )
        is None
    )


def test_archive_scope_observes_completion_and_collision_preservation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _scope_dependencies(monkeypatch, state="completion_transition")
    completion = _scope_report(
        tmp_path,
        changed_paths=(ACTIVE,),
    )
    assert completion is not None
    assert completion["verdict"] == "pass"

    _scope_dependencies(monkeypatch, state="archive_transition")
    source = CARRIER.removesuffix("/commitment.toml")
    preserved = "openspec/changes/archive/preserved-change"

    def git_stdout(_root: Path, *args: str) -> str:
        revision = args[-1]
        if revision in {f"{HEAD}:{source}", f"{TREE}:{source}", f"{TREE}:{preserved}"}:
            return "source-tree"
        return ""

    monkeypatch.setattr(archive, "git_stdout", git_stdout)
    monkeypatch.setattr(archive, "collision_preservation_path", lambda *_args: preserved)
    archived = _scope_report(
        tmp_path,
        changed_paths=(CARRIER,),
        preserved_archive=(source, preserved),
    )
    assert archived is not None
    assert archived["verdict"] == "pass"


@pytest.mark.parametrize("case", ["invalid-carrier", "non-merge", "not-relocated", "no-collision"])
def test_post_archive_preservation_is_observable_through_scope_report(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, case: str
) -> None:
    carrier = "invalid" if case == "invalid-carrier" else CARRIER
    _scope_dependencies(monkeypatch, state="post_archive_closeout", carrier=carrier)
    source = carrier.removesuffix("/commitment.toml")

    def git_stdout(_root: Path, *args: str) -> str:
        if args[:2] == ("rev-list", HEAD):
            return "revision"
        if args == ("rev-parse", f"parent:{source}"):
            return "" if case == "no-collision" else "source-tree"
        return ""

    monkeypatch.setattr(archive, "git_stdout", git_stdout)
    monkeypatch.setattr(
        archive,
        "run_git",
        lambda *_args, **_kwargs: SimpleNamespace(
            stdout="revision parent\n" if case != "non-merge" else "revision\n"
        ),
    )
    monkeypatch.setattr(
        archive,
        "exact_carrier_relocation",
        lambda *_args: case != "not-relocated",
    )

    report = _scope_report(
        tmp_path,
        changed_paths=(carrier,),
    )
    if case == "no-collision":
        assert report is not None
        assert report["verdict"] == "pass"
    else:
        assert report is None


def test_post_archive_scope_binds_exact_collision_copy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _scope_dependencies(monkeypatch, state="post_archive_closeout")
    source = CARRIER.removesuffix("/commitment.toml")
    preserved = "openspec/changes/archive/preserved-change"

    def git_stdout(_root: Path, *args: str) -> str:
        if args[:2] == ("rev-list", HEAD):
            return "revision"
        if args == ("rev-parse", f"parent:{source}"):
            return "source-tree"
        if args[-1] in {
            f"parent:{source}",
            f"{TREE}:{source}",
            f"{TREE}:{preserved}",
        }:
            return "source-tree"
        return ""

    monkeypatch.setattr(archive, "git_stdout", git_stdout)
    monkeypatch.setattr(
        archive,
        "run_git",
        lambda *_args, **_kwargs: SimpleNamespace(stdout="revision parent\n"),
    )
    monkeypatch.setattr(archive, "exact_carrier_relocation", lambda *_args: True)
    monkeypatch.setattr(archive, "collision_preservation_path", lambda *_args: preserved)
    monkeypatch.setattr(archive, "current_tree", lambda *_args: TREE)

    report = _scope_report(
        tmp_path,
        changed_paths=(CARRIER,),
        preserved_archive=(source, preserved),
    )
    assert report is not None
    assert report["verdict"] == "pass"


def test_archive_scope_rejects_invalid_profile_through_public_report(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _scope_dependencies(monkeypatch, state="completion_transition")
    monkeypatch.setattr(archive, "load_repository_profile", lambda _root: _profile(valid=False))

    with pytest.raises(ValueError, match=INVALID_PROFILE_ERROR):
        _scope_report(
            tmp_path,
            changed_paths=(ACTIVE,),
        )
