"""Archive candidates share verification work, never authority across observations."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import ethos.adapters.openspec.lifecycle.archive_provenance as provenance
import ethos.adapters.openspec.lifecycle.archive_transition as archive
import ethos.adapters.repo.commit.rewrite as rewrite
from ethos.adapters.repo.commit.history import prepare_history_repair
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.semantic import commitment_fixture

TRAILER = "Co-authored-by: Legacy Agent <legacy@example.invalid>"


@pytest.mark.parametrize("valid", [False, True])
@pytest.mark.parametrize("related", [False, True])
def test_archive_candidates_verify_repair_once_per_fresh_observation(
    tmp_path, monkeypatch, valid, related
):
    """Native ancestry selects the same archive with bounded verification calls."""
    root = init_git_repo(tmp_path / "repo")
    archive_path = "openspec/changes/archive/2026-09-16-fixture"
    artifact = root / archive_path / "proposal.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("Preserved official archive.\n")
    base = commit_fixture(root, "archive content")
    tree = git(root, "rev-parse", f"{base}^{{tree}}")

    def commit(parent, message):
        return git(root, "commit-tree", tree, "-p", parent, "-m", message)

    old_first = commit(base, f"chain first\n\n{TRAILER}")
    old_last = commit(old_first, "chain last")
    prepared = prepare_history_repair(
        root,
        old_last,
        corrections={old_first: {"remove_attribution_trailers": [TRAILER]}},
    )
    new_first, new_last = prepared["mapping"][old_first], prepared["replacement"]
    records = tuple(
        SimpleNamespace(
            id=change,
            predicate="effect:git-ref-update",
            verifier="fixture",
            effect_digest=change,
            payload=SimpleNamespace(body={"plan": {"policy": {"transition": "openspec.archive"}}}),
        )
        for change in ("first", "last")
    )
    repair_record = SimpleNamespace(
        id="repair",
        predicate=provenance.RESULT,
        payload=SimpleNamespace(
            body={
                "coordinates": {
                    "old": old_last,
                    "history": {
                        "corrections": {old_first: {"remove_attribution_trailers": [TRAILER]}}
                    },
                },
                "replacement": new_last,
            }
        ),
    )
    selected = (*records, repair_record)
    plans = {
        record.id: SimpleNamespace(
            policy={
                "transition": "openspec.archive",
                "change": record.id,
                "branch": "work/fixture",
            },
            facts={"values": {"changed_paths": [str(artifact)], "archive_path": archive_path}},
            commitment=commitment_fixture(id=f"change:{record.id}").model_dump(),
            digest=record.id,
            effect=SimpleNamespace(
                updates={"refs/heads/work/fixture": SimpleNamespace(desired=head)}
            ),
        )
        for record, head in zip(records, (old_first, old_last), strict=True)
    }
    verified = []
    effect_checks = []

    def verify(observed_root, *, new, attestations):
        assert observed_root == root
        assert new == new_last
        assert attestations is selected
        verified.append(new)
        return (
            {
                "mapping": {old_first: new_first, old_last: new_last},
                "attestation_id": "repair",
            }
            if valid
            else None
        )

    def validate_effect(_root, _effect, record, **_kwargs):
        effect_checks.append(record.id)

    monkeypatch.setattr(archive, "read_attestation_set", lambda _root: ("selected", selected))
    monkeypatch.setattr(archive, "plan_from_attestation", lambda record: plans[record.id])
    monkeypatch.setattr(archive, "git_effect_from_plan", lambda plan: plan.effect)
    monkeypatch.setattr(archive, "validate_git_effect_attestation", validate_effect)
    monkeypatch.setattr(provenance, "validated_refresh_edge", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(provenance, "completed_signature_repair", verify)
    native_git = Mock(wraps=provenance.run_git)
    monkeypatch.setattr(provenance, "run_git", native_git)
    original_refs = git(root, "show-ref")

    for attempt in (1, 2):
        result = archive.attested_archive_transition(
            root, head=new_last if related else commit(base, "unrelated current history")
        )
        if valid and related:
            assert result is not None
            assert result[0].id == "change:last"
            assert result[1]["resolved_head"] == new_last
            assert result[1]["repair_attestation_ids"] == ["repair"]
            assert effect_checks == ["first", "last"]
        else:
            assert result is None
            assert effect_checks == []
        assert verified == ([new_last] * attempt if related else [])
        effect_checks.clear()
        valid = not valid
    assert not any(
        args[:2] == ("rev-list", "--count") and args[2].endswith(f"..{old_last}")
        for args in (call.args for call in native_git.call_args_list)
    )
    assert git(root, "show-ref") == original_refs


def test_unaffected_archive_ancestor_does_not_demand_history_verification(tmp_path, monkeypatch):
    """An ancestor before the correction is not a dependency of its replacement DAG."""
    root = init_git_repo(tmp_path / "repo")
    archive_path = "openspec/changes/archive/2026-09-16-fixture"
    artifact = root / archive_path / "proposal.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("Preserved official archive.\n")
    archived = commit_fixture(root, "archive before correction")
    tree = git(root, "rev-parse", f"{archived}^{{tree}}")
    old = git(root, "commit-tree", tree, "-p", archived, "-m", "old corrected tip")
    replacement = git(root, "commit-tree", tree, "-p", archived, "-m", "replacement tip")
    current = git(root, "commit-tree", tree, "-m", "unrelated current history")
    record = SimpleNamespace(
        predicate=provenance.RESULT,
        payload=SimpleNamespace(
            body={
                "coordinates": {
                    "old": old,
                    "history": {"corrections": {old: {"resign": True}}},
                },
                "replacement": replacement,
            }
        ),
    )
    verified = []

    def verify(_root, *, new, **_kwargs):
        verified.append(new)
        return {"mapping": {old: replacement}, "attestation_id": "repair"}

    monkeypatch.setattr(provenance, "validated_refresh_edge", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(provenance, "completed_signature_repair", verify)
    original_refs = git(root, "show-ref")
    result = provenance.resolve_archive_head(
        root,
        archived_head=archived,
        current_head=current,
        branch="work/fixture",
        archive_path=archive_path,
        attestations=(record,),
        repairs={},
    )
    assert result is None
    assert verified == []
    assert git(root, "show-ref") == original_refs


def test_archive_resolution_selects_exact_refresh_predecessor(tmp_path, monkeypatch):
    """An unrelated refresh input cannot require plan decoding for this archive."""
    root = init_git_repo(tmp_path / "repo")
    archive_path = "openspec/changes/archive/2026-09-16-fixture"
    artifact = root / archive_path / "proposal.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("Preserved official archive.\n")
    old = commit_fixture(root, "archive input")
    tree = git(root, "rev-parse", f"{old}^{{tree}}")
    current = git(root, "commit-tree", tree, "-m", "unrelated current history")
    record = SimpleNamespace(
        predicate="effect:git-ref-update",
        payload=SimpleNamespace(
            body={
                "plan": {
                    "policy": {"transition": "lane.refresh", "execution_branch": "work/fixture"},
                    "effect": {
                        "updates": {
                            "refs/heads/work/fixture": {"expected": current, "desired": old}
                        }
                    },
                }
            }
        ),
    )
    decoded = []

    def invalid_plan(candidate):
        decoded.append(candidate)
        message = "invalid selected plan"
        raise ValueError(message)

    monkeypatch.setattr(rewrite, "plan_from_attestation", invalid_plan)
    refs = git(root, "show-ref")
    assert (
        provenance.resolve_archive_head(
            root,
            archived_head=old,
            current_head=current,
            branch="work/fixture",
            archive_path=archive_path,
            attestations=(record,),
            repairs={},
        )
        is None
    )
    assert decoded == []
    assert git(root, "show-ref") == refs


@pytest.mark.parametrize("reader", ["archive", "refresh"])
@pytest.mark.parametrize("relevant", [False, True])
@pytest.mark.parametrize("same_branch", [False, True])
def test_archive_readers_decode_only_relevant_effect_plans(
    tmp_path, monkeypatch, reader, relevant, same_branch
):
    """A selector skips irrelevant plans but never accepts an unvalidated candidate."""
    transition = "openspec.archive" if reader == "archive" else "lane.refresh"
    record = SimpleNamespace(
        predicate="effect:git-ref-update",
        payload=SimpleNamespace(
            body={
                "plan": {
                    "policy": {
                        "transition": transition if relevant else "lane.retire",
                        "execution_branch": "work/fixture" if same_branch else "work/peer",
                    }
                }
            }
        ),
    )
    decoded = []

    def invalid_plan(candidate):
        decoded.append(candidate)
        message = "invalid selected plan"
        raise ValueError(message)

    owner = archive if reader == "archive" else rewrite
    monkeypatch.setattr(owner, "plan_from_attestation", invalid_plan)
    if reader == "archive":
        monkeypatch.setattr(archive, "read_attestation_set", lambda _root: ("selected", (record,)))
        result = archive.attested_archive_transition(tmp_path, head="head")
    else:
        result = rewrite.validated_refresh_edge(tmp_path, branch="work/fixture", attestation=record)
    assert result is None
    assert decoded == ([record] if relevant and (reader == "archive" or same_branch) else [])
