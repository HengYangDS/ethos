"""Single-owner OpenSpec generation observation contracts."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

import pytest
import tomli_w

import ethos.adapters.openspec.generation.attestation as effect_authority
from ethos.adapters.admission.transitions import work_lane_ref_transition_report
from ethos.adapters.openspec.start_effect import current_generation_scope
from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.git_effect_attestation import NativeEffect
from ethos.adapters.repo.git_effect_attestation import issue_native_effect
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.semantic import Attestation
from tests.support.governed_repository import exact_lease
from tests.support.governed_repository import git
from tests.support.governed_repository import start_adopted_candidate
from tests.support.semantic import commitment_v2

if TYPE_CHECKING:
    from pathlib import Path


def test_archive_reactivation_is_one_current_generation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repository, candidate = start_adopted_candidate(tmp_path)
    archive = candidate / "openspec/changes/archive/2026-08-08-restored-change"
    archive.mkdir(parents=True)
    (archive / ".openspec.yaml").write_text("schema: spec-driven\n")
    (archive / "commitment.toml").write_text(
        tomli_w.dumps(
            commitment_v2(
                id="change:restored-change",
                intent="Restore one exact accepted archive.",
                subjects=(load_repository_commitment(candidate).id,),
                scope=("README.md", "openspec/changes/restored-change/**"),
            ).model_dump(mode="python")
        )
    )
    git(candidate, "add", archive.relative_to(candidate).as_posix())
    git(candidate, "commit", "-m", "archive restored change")
    accepted = git(candidate, "rev-parse", "HEAD")
    worktree, branch = tmp_path / "repo-work-restored-change", "work/restored-change"
    git(candidate, "worktree", "add", "-b", branch, worktree.as_posix(), accepted)
    active = worktree / "openspec/changes/restored-change"
    active.parent.mkdir(parents=True, exist_ok=True)
    (worktree / archive.relative_to(candidate)).rename(active)
    git(worktree, "add", "-A")
    git(worktree, "commit", "-m", "reactivate exact accepted archive")
    restored = git(worktree, "rev-parse", "HEAD")
    acquire_lease(
        state_database(repository),
        lease=exact_lease(
            repo=repository,
            branch=branch,
            holder_ref="agent:test:case:reactivation",
            expected_head=restored,
            carrier="openspec/changes/restored-change/commitment.toml",
            change_id="restored-change",
        ),
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:reactivation")
    (worktree / "README.md").write_text("# restored generation\n")
    git(worktree, "add", "README.md")
    git(worktree, "commit", "-m", "implement restored generation")
    implemented = git(worktree, "rev-parse", "HEAD")
    assert (
        work_lane_ref_transition_report(
            root=worktree,
            phase="committed",
            ref_name=f"refs/heads/{branch}",
            old_value=restored,
            new_value=implemented,
        )["state"]
        == "lease_ref_advanced"
    )

    lease = leases_by_branch(worktree)[branch]
    scope = current_generation_scope(
        worktree,
        head=implemented,
        repository_id=load_repository_commitment(worktree).id,
        commitment=load_commitment(
            worktree,
            carrier=str(lease["base_commitment_path"]),
            change_id="restored-change",
            tree_ref=implemented,
        ),
        lease=lease,
        fallback_paths=(
            "README.md",
            "openspec/changes/restored-change/.openspec.yaml",
            "openspec/changes/restored-change/commitment.toml",
        ),
    )

    assert scope.gaps == ()
    assert scope.start_authority["predicate"] == "effect:openspec-archive-reactivation"
    assert {item.source for item in scope.attributions if item.state == "authorized"} == {
        "archive_reactivation"
    }


def test_start_effect_rejects_unknown_round_tripped_attestation_kind(
    tmp_path: Path,
) -> None:
    commitment = commitment_v2(
        id="change:test-change",
        intent="Test start authority.",
        subjects=("repository:test",),
    )
    issued = issue_native_effect(
        tmp_path,
        effect=NativeEffect(
            "effect:openspec-change-start",
            "openspec.change.start",
            ("ethos", "lane", "start-change"),
            {"change": "test-change"},
            {},
            {},
        ),
        state="applied",
        commitment_digest=commitment.digest(),
        repository_id="repository:test",
    )
    payload = issued.model_dump(mode="python", exclude={"id"})
    payload["payload"] = {"kind": "effect:unknown", "body": issued.payload.body}
    unknown = Attestation.issue(payload)

    assert Attestation.model_validate_json(unknown.canonical_json()) == unknown
    assert (
        effect_authority.start_effect_authority(
            tmp_path, unknown, "1" * 40, "repository:test", commitment, {}
        )
        == {}
    )


@pytest.mark.parametrize("flaw", ["predecessor", "current-holder", "verdict"])
def test_start_effect_requires_predecessor_and_current_holder_continuity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    flaw: str,
) -> None:
    repository, previous_head, head = "repository:test", "1" * 40, "2" * 40
    predecessor = "a" * 64
    successor = commitment_v2(
        id="change:test-change",
        intent="Test successor authority.",
        subjects=(repository,),
        predecessors=(("b" * 64) if flaw == "predecessor" else predecessor,),
    )
    old = lease_generation(
        {
            "lane_ref": "work/test-change",
            "lane_incarnation_id": "lane:test-change",
            "lease_id": "lease:test-change",
            "epoch": 1,
            "holder_ref": "agent:test",
            "expected_head": previous_head,
            "expected_tree": "3" * 40,
            "base_commitment_path": (
                "openspec/changes/archive/2026-08-14-test-change/commitment.toml"
            ),
            "base_commitment_bytes_sha256": "c" * 64,
            "base_commitment_digest": predecessor,
            "issued_at": "2026-08-15T00:00:00Z",
            "renewed_at": "2026-08-15T00:00:00Z",
            "path_scope": (),
            "expires_at": "2026-08-16T00:00:00Z",
            "payload_sha256": "d" * 64,
        }
    )
    new = old | {
        "epoch": 2,
        "expected_head": head,
        "expected_tree": "4" * 40,
        "base_commitment_path": "openspec/changes/test-change/commitment.toml",
        "base_commitment_bytes_sha256": "e" * 64,
        "base_commitment_digest": successor.digest(),
    }
    receipt = issue_native_effect(
        tmp_path,
        effect=NativeEffect(
            "effect:openspec-change-start",
            "openspec.change.start",
            ("ethos", "lane", "start-change"),
            {"change": "test-change", "previous_head": previous_head, "head": head},
            {"head": previous_head, "lease": old},
            {"head": head, "lease": new},
        ),
        state="applied",
        commitment_digest=successor.digest(),
        repository_id=repository,
    )
    if flaw == "verdict":
        payload = receipt.model_dump(mode="python", exclude={"id"})
        payload.update(verdict="block")
        payload["payload"] = {
            "kind": "effect:native",
            "body": receipt.payload.body | {"required_gaps": ("authority_denied",)},
        }
        receipt = Attestation.issue(payload)
    monkeypatch.setattr(
        effect_authority,
        "load_lease_bound_commitment",
        lambda *_args, **_kwargs: successor,
    )
    monkeypatch.setattr(
        effect_authority,
        "current_tree",
        lambda _root, ref: {previous_head: "3" * 40, head: "4" * 40}[ref],
    )
    monkeypatch.setattr(
        effect_authority,
        "git_stdout",
        lambda _root, *_args: previous_head,
    )
    monkeypatch.setattr(effect_authority, "is_ancestor", lambda *_args: True)

    assert (
        effect_authority.start_effect_authority(
            tmp_path,
            receipt,
            head,
            repository,
            successor,
            {
                "lane_ref": "work/test-change",
                **new,
                **({"holder_ref": "agent:other"} if flaw == "current-holder" else {}),
            },
        )
        == {}
    )


def test_archive_effect_requires_exact_discriminator_verifier_validity_and_bindings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repository, head = "repository:test", "1" * 40
    archive = "openspec/changes/archive/2026-01-01-test-change"
    commitment = commitment_v2(
        id="change:test-change",
        intent="Test archive authority.",
        subjects=(repository,),
    )
    lease: dict[str, object] = {"lease_id": "lease:test", "expected_head": head}
    valid = issue_native_effect(
        tmp_path,
        effect=NativeEffect(
            "effect:openspec-archive",
            "openspec.archive",
            ("openspec", "archive"),
            {"change": "test-change", "archive_path": archive},
            {},
            {
                "head": head,
                "tree": "2" * 40,
                "archive_path": archive,
                "changed_paths": (f"{archive}/commitment.toml",),
                "lease": lease,
            },
        ),
        state="applied",
        commitment_digest=commitment.digest(),
        repository_id=repository,
    )
    base = valid.model_dump(mode="python", exclude={"id"})
    stale = datetime(2020, 1, 1, tzinfo=UTC)
    mutations = (
        {"predicate": "effect:unknown"},
        {"payload": {"kind": "effect:unknown", "body": valid.payload.body}},
        {"verifier": "agent:test:unknown"},
        {"issued_at": stale, "valid_from": stale, "valid_until": stale},
        {"commitment_digest": None},
        {"effect_digest": None},
    )
    monkeypatch.setattr(effect_authority, "current_tree", lambda *_args: "2" * 40)
    monkeypatch.setattr(effect_authority, "exact_archive_paths", lambda *_args: True)

    assert effect_authority.archive_effect_authority(
        tmp_path, valid, head, repository, commitment, lease
    )
    assert all(
        not effect_authority.archive_effect_authority(
            tmp_path,
            Attestation.issue(base | mutation),
            head,
            repository,
            commitment,
            lease,
        )
        for mutation in mutations
    )
