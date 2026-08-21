"""Single-owner OpenSpec generation observation contracts."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

import pytest
import tomli_w

import ethos.adapters.mutation.lane_lifecycle.commitment_rebind_evidence as rebind_evidence
import ethos.adapters.openspec.generation.attestation as effect_authority
import ethos.adapters.openspec.lifecycle.archive_effect as archive_effect
import ethos.adapters.openspec.start_effect as start_effect
from ethos.adapters.admission.transitions import work_lane_ref_transition_report
from ethos.adapters.openspec.start_effect import current_generation_scope
from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.native_effect_attestation import NativeEffect
from ethos.adapters.repo.native_effect_attestation import issue_native_effect
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.semantic import Attestation
from tests.support.governed_repository import exact_lease
from tests.support.governed_repository import git
from tests.support.governed_repository import start_adopted_candidate
from tests.support.semantic import commitment_fixture

if TYPE_CHECKING:
    from pathlib import Path


def _rebind_attestation(ordinal: int) -> Attestation:
    return Attestation.issue(
        {
            "schema_version": 2,
            "predicate": "effect:commitment-rebind",
            "verifier": "agent:test:generation-observation",
            "subject": f"commitment-rebind:{ordinal:064x}",
            "issued_at": datetime(2026, 8, 21, tzinfo=UTC),
            "valid_from": datetime(2026, 8, 21, tzinfo=UTC),
            "valid_until": None,
            "verdict": "pass",
            "payload": {"kind": "effect:commitment-rebind", "body": {"ordinal": ordinal}},
            "relations": (),
            "advisories": (),
            "evidence_refs": (),
            "commitment_digest": f"{ordinal + 1:064x}",
            "facts_digest": f"{ordinal + 2:064x}",
            "plan_digest": f"{ordinal + 3:064x}",
            "policy_digest": f"{ordinal + 4:064x}",
            "effect_digest": f"{ordinal:064x}",
            "mints_authority": False,
        }
    )


def test_generation_authorities_reuse_one_attestation_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    attestations = (_rebind_attestation(1), _rebind_attestation(2))
    reads = 0
    observed: list[tuple[Attestation, ...]] = []

    def read_once(_root: Path) -> tuple[str, tuple[Attestation, ...]]:
        nonlocal reads
        reads += 1
        return "selected-root", attestations

    def rebind_authority(
        _root: Path,
        _attestation: Attestation,
        *,
        repository_id: str,
        commitment_digest: str,
        lease: dict[str, object],
        attestations: tuple[Attestation, ...],
    ) -> dict[str, object]:
        del repository_id, commitment_digest, lease
        observed.append(attestations)
        return {}

    monkeypatch.setattr(start_effect, "read_attestation_set", read_once)
    monkeypatch.setattr(start_effect, "rebind_generation_authority", rebind_authority)
    monkeypatch.setattr(start_effect, "changed_paths", lambda _root: ())
    monkeypatch.setattr(start_effect, "_archive_reactivation", lambda *_args: {})
    monkeypatch.setattr(start_effect, "_initial_generation", lambda *_args: "")

    start_effect.current_generation_scope(
        tmp_path,
        head="a" * 40,
        repository_id="repository:test",
        commitment=commitment_fixture(
            id="change:test",
            intent="Reuse one observed Attestation snapshot.",
            subjects=("repository:test",),
        ),
        lease={},
        fallback_paths=(),
    )

    assert reads == 1
    assert observed == [attestations, attestations]


def test_rebind_authority_rejects_stale_generation_before_deep_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    current: dict[str, object] = {
        "branch": "work/current",
        "lane_incarnation_id": "lane-incarnation:current",
        "lease_id": "lease:current",
        "holder_ref": "agent:test:current",
        "epoch": 7,
        "expected_head": "a" * 40,
        "expected_tree": "b" * 40,
        "base_commitment_path": "openspec/changes/current/commitment.toml",
        "base_commitment_bytes_sha256": "c" * 64,
        "base_commitment_digest": "d" * 64,
    }
    stale = dict(current, lease_id="lease:stale", epoch=6)
    attestation = Attestation.issue(
        {
            "schema_version": 2,
            "predicate": "effect:commitment-rebind",
            "verifier": current["holder_ref"],
            "subject": f"commitment-rebind:{'e' * 64}",
            "issued_at": datetime(2026, 8, 21, tzinfo=UTC),
            "valid_from": datetime(2026, 8, 21, tzinfo=UTC),
            "valid_until": None,
            "verdict": "pass",
            "payload": {
                "kind": "effect:commitment-rebind",
                "body": {
                    "claim": {"operation": "commitment-rebind", "branch": "work/current"},
                    "old_lease_generation": dict(stale, epoch=5),
                    "new_lease_generation": stale,
                    "result": {"git": "applied", "lease": "epoch_advanced"},
                },
            },
            "relations": (),
            "advisories": (),
            "evidence_refs": (),
            "commitment_digest": "f" * 64,
            "facts_digest": "1" * 64,
            "plan_digest": "2" * 64,
            "policy_digest": "3" * 64,
            "effect_digest": "e" * 64,
            "mints_authority": False,
        }
    )
    monkeypatch.setattr(
        rebind_evidence,
        "validated_plan_attestation",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("stale_generation_must_not_reach_deep_validation")
        ),
    )

    assert (
        rebind_evidence.rebind_generation_authority(
            tmp_path,
            attestation,
            repository_id="repository:test",
            commitment_digest=str(current["base_commitment_digest"]),
            lease=current,
            attestations=(attestation,),
        )
        == {}
    )


def test_archive_reactivation_is_one_current_generation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repository, candidate = start_adopted_candidate(tmp_path)
    archive = candidate / "openspec/changes/archive/2026-08-08-restored-change"
    archive.mkdir(parents=True)
    (archive / ".openspec.yaml").write_text("schema: spec-driven\n")
    (archive / "commitment.toml").write_text(
        tomli_w.dumps(
            commitment_fixture(
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
    commitment = commitment_fixture(
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
    successor = commitment_fixture(
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
    repository, previous_head, head = "repository:test", "0" * 40, "1" * 40
    tree = "2" * 40
    archive = "openspec/changes/archive/2026-01-01-test-change"
    paths = (f"{archive}/commitment.toml",)
    commitment = commitment_fixture(
        id="change:test-change",
        intent="Test archive authority.",
        subjects=(repository,),
    )
    lease: dict[str, object] = {"lease_id": "lease:test", "expected_head": head}
    monkeypatch.setattr(archive_effect, "current_tree", lambda *_args: tree)
    monkeypatch.setattr(archive_effect, "exact_archive_paths", lambda *_args: True)
    effect_identity = archive_effect.archive_effect_identity(
        tmp_path,
        change="test-change",
        head=previous_head,
        tree=tree,
        changed_paths=paths,
    )

    def issue(identity: str) -> Attestation:
        return issue_native_effect(
            tmp_path,
            effect=NativeEffect(
                "effect:openspec-archive",
                "openspec.archive",
                ("openspec", "archive"),
                {"change": "test-change", "archive_path": archive},
                {"head": previous_head, "effect_identity": identity},
                {
                    "head": head,
                    "tree": tree,
                    "archive_path": archive,
                    "changed_paths": paths,
                    "lease": lease,
                },
            ),
            state="applied",
            commitment_digest=commitment.digest(),
            repository_id=repository,
        )

    valid = issue(effect_identity)
    wrong_effect = issue("0" * 64)
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

    assert archive_effect.archive_effect_authority(
        tmp_path, valid, head, repository, commitment, lease
    )
    assert not archive_effect.archive_effect_authority(
        tmp_path, wrong_effect, head, repository, commitment, lease
    )
    assert all(
        not archive_effect.archive_effect_authority(
            tmp_path,
            Attestation.issue(base | mutation),
            head,
            repository,
            commitment,
            lease,
        )
        for mutation in mutations
    )
