"""Archive candidates share verification work, never authority across observations."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import ethos.adapters.openspec.lifecycle.archive_provenance as provenance
import ethos.adapters.openspec.lifecycle.archive_transition as archive
import ethos.adapters.repo.commit.rewrite as rewrite
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.semantic import commitment_fixture


@pytest.mark.parametrize("initially_valid", [False, True])
def test_archive_candidates_verify_repair_once_per_fresh_observation(
    tmp_path, monkeypatch, initially_valid
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

    old_first = commit(base, "old first")
    old_last = commit(old_first, "old last")
    new_first = commit(base, "new first")
    new_last = commit(new_first, "new last")
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
        payload=SimpleNamespace(body={"coordinates": {"old": old_last}, "replacement": new_last}),
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
    valid = initially_valid

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
    monkeypatch.setattr(provenance, "refresh_edges", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(provenance, "completed_signature_repair", verify)
    original_refs = git(root, "show-ref")

    for attempt in (1, 2):
        result = archive.attested_archive_transition(root, head=new_last)
        if valid:
            assert result is not None
            assert result[0].id == "change:last"
            assert result[1]["resolved_head"] == new_last
            assert result[1]["repair_attestation_ids"] == ["repair"]
            assert effect_checks == ["first", "last"]
        else:
            assert result is None
            assert effect_checks == []
        assert verified == [new_last] * attempt
        effect_checks.clear()
        valid = not valid
    assert git(root, "show-ref") == original_refs


@pytest.mark.parametrize("reader", ["archive", "refresh"])
@pytest.mark.parametrize("relevant", [False, True])
def test_archive_readers_decode_only_relevant_effect_plans(tmp_path, monkeypatch, reader, relevant):
    """A selector skips irrelevant plans but never accepts an unvalidated candidate."""
    transition = "openspec.archive" if reader == "archive" else "lane.refresh"
    record = SimpleNamespace(
        predicate="effect:git-ref-update",
        payload=SimpleNamespace(
            body={"plan": {"policy": {"transition": transition if relevant else "lane.retire"}}}
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
    assert decoded == ([record] if relevant else [])
