# ruff: noqa: SLF001
from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.openspec.lifecycle.archive_transition as archive
from ethos.contracts.semantic import Commitment
from ethos.repository.profile import INVALID_PROFILE_ERROR

if TYPE_CHECKING:
    from pathlib import Path


HEAD = "a" * 40
TREE = "b" * 40
CARRIER = "openspec/changes/archive/2026-08-10-change/commitment.toml"
ACTIVE = "openspec/changes/change/commitment.toml"


def _commitment(*, change_identity: bool = True) -> Commitment:
    return Commitment(
        id="change:change" if change_identity else "change",
        intent="Archive exact governed work.",
        subjects=("repository:test",),
        scope=("openspec/changes/change/**",),
    )


def _lease(**updates: object) -> dict[str, object]:
    lease: dict[str, object] = {
        "lease_state": "valid",
        "expected_head": HEAD,
        "base_commitment_digest": _commitment().digest(),
    }
    lease.update(updates)
    return lease


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
        archive, "archive_binding", lambda *_a, **_k: ("archive_transition", TREE, CARRIER)
    )
    monkeypatch.setattr(
        archive,
        "load_commitment",
        lambda *_a, **_k: (_ for _ in ()).throw(ValueError("invalid archive")),
    )
    assert archive.lease_bound_archive_scope_report(tmp_path, official_change_complete=True) is None


def test_archive_transition_fields_require_valid_lease_and_exact_target(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(archive, "git_stdout", lambda *_a, **_k: "work/feature")
    monkeypatch.setattr(archive, "leases_by_branch", lambda _root: {"work/feature": {}})
    assert archive.lease_bound_archive_transition_fields(tmp_path, target_head=HEAD) is None

    source = _commitment()
    target = {
        "base_commitment_path": CARRIER,
        "base_commitment_digest": source.digest(),
        "base_commitment_bytes_sha256": "bytes",
        "expected_tree": TREE,
    }
    monkeypatch.setattr(archive, "leases_by_branch", lambda _root: {"work/feature": _lease()})
    monkeypatch.setattr(archive, "load_lease_bound_commitment", lambda *_a, **_k: source)
    monkeypatch.setattr(archive, "current_tree", lambda *_a: TREE)
    monkeypatch.setattr(archive, "staged_archive_carrier", lambda *_a, **_k: CARRIER)
    monkeypatch.setattr(archive, "exact_commitment_fields", lambda *_a, **_k: target)
    monkeypatch.setattr(archive, "load_commitment", lambda *_a, **_k: source)
    monkeypatch.setattr(archive, "_preserved_archive_binding", lambda *_a, **_k: (True, None))
    monkeypatch.setattr(archive, "active_commitments", lambda *_a: ())
    assert archive.lease_bound_archive_transition_fields(tmp_path, target_head=HEAD) == target


def test_archive_preservation_dispatches_completion_collision_and_closeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    assert archive._archive_preservation_binding(
        tmp_path, state="completion_transition", head=HEAD, tree=TREE, carrier=CARRIER
    ) == (True, None)
    monkeypatch.setattr(archive, "git_stdout", lambda *_a, **_k: "archive-tree")
    monkeypatch.setattr(archive, "collision_preservation_path", lambda *_a: "preserved")
    monkeypatch.setattr(archive, "_exact_preserved_archive", lambda *_a, **_k: True)
    assert archive._archive_preservation_binding(
        tmp_path, state="archive_transition", head=HEAD, tree=TREE, carrier=CARRIER
    ) == (True, (CARRIER.removesuffix("/commitment.toml"), "preserved"))

    monkeypatch.setattr(
        archive,
        "_post_archive_preservation_binding",
        lambda *_a, **_k: (False, ("source", "target")),
    )
    assert archive._archive_preservation_binding(
        tmp_path, state="post_archive_closeout", head=HEAD, tree=TREE, carrier=CARRIER
    ) == (False, ("source", "target"))


@pytest.mark.parametrize("case", ["invalid-carrier", "non-merge", "not-relocated", "no-collision"])
def test_post_archive_preservation_rejects_unproven_history(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, case: str
) -> None:
    carrier = "invalid" if case == "invalid-carrier" else CARRIER
    monkeypatch.setattr(
        archive,
        "git_stdout",
        lambda _root, *args: (
            "revision"
            if args[:2] == ("rev-list", HEAD)
            else ""
            if case == "no-collision"
            else "tree"
        ),
    )
    monkeypatch.setattr(
        archive,
        "run_git",
        lambda *_a, **_k: SimpleNamespace(
            stdout="revision parent\n" if case != "non-merge" else "revision\n"
        ),
    )
    monkeypatch.setattr(
        archive,
        "exact_carrier_relocation",
        lambda *_a: case != "not-relocated",
    )
    result = archive._post_archive_preservation_binding(tmp_path, head=HEAD, carrier=carrier)
    assert result == ((True, None) if case == "no-collision" else (False, None))


def test_post_archive_preservation_binds_exact_collision_copy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = CARRIER.removesuffix("/commitment.toml")

    def git_stdout(_root: Path, *args: str) -> str:
        if args[:2] == ("rev-list", HEAD):
            return "revision"
        if args == ("rev-parse", f"parent:{source}"):
            return "source-tree"
        return ""

    monkeypatch.setattr(archive, "git_stdout", git_stdout)
    monkeypatch.setattr(
        archive, "run_git", lambda *_a, **_k: SimpleNamespace(stdout="revision parent\n")
    )
    monkeypatch.setattr(archive, "exact_carrier_relocation", lambda *_a: True)
    monkeypatch.setattr(archive, "collision_preservation_path", lambda *_a: "preserved")
    monkeypatch.setattr(archive, "current_tree", lambda *_a: TREE)
    monkeypatch.setattr(archive, "_exact_preserved_archive", lambda *_a, **_k: True)
    assert archive._post_archive_preservation_binding(tmp_path, head=HEAD, carrier=CARRIER) == (
        True,
        (source, "preserved"),
    )


def test_exact_preserved_archive_and_invalid_profile_are_fail_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    values = iter(("source", "replacement", "source"))
    monkeypatch.setattr(archive, "git_stdout", lambda *_a, **_k: next(values))
    assert archive._exact_preserved_archive(
        tmp_path, head=HEAD, tree=TREE, source="source", target="target"
    )

    monkeypatch.setattr(
        archive,
        "load_repository_profile",
        lambda _root: SimpleNamespace(state="invalid", declaration=None),
    )
    with pytest.raises(ValueError, match=INVALID_PROFILE_ERROR):
        archive._scope_report(
            tmp_path,
            commitment=_commitment(),
            change="change",
            carrier=CARRIER,
            state="archive_transition",
            changed_paths=(ACTIVE,),
        )
