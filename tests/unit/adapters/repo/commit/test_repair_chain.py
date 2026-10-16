"""Resolve original peer objects through consecutive, completed native repairs."""

from __future__ import annotations

import pytest

import ethos.adapters.repo.commit.signature as signature
from ethos.adapters.mutation.publication.request import observe_remote_publication_effect
from ethos.adapters.repo.attestation_set import ATTESTATION_SET_REF
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.adapters.repo.commit.conservation import accepted_contribution
from ethos.adapters.repo.commit.integration import commit_range_admission_report
from ethos.adapters.repo.commit.signature import RESULT
from ethos.adapters.repo.commit.signature import repaired_object_provenance
from ethos.adapters.repo.commit.signature import repaired_peer_ref_provenance
from ethos.adapters.repo.git import is_ancestor
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import git
from tests.support.governed_repository import write_release_mirror
from tests.support.signature import repair_fixture_history
from tests.support.signature import signature_repository

TRAILER = "Co-authored-by: Legacy Agent <legacy@example.invalid>"


def _consecutive_repairs(tmp_path, monkeypatch, *, independent: bool = False):
    repo, initial, candidate = signature_repository(tmp_path, coupled=True)
    (repo / "peer.txt").write_text("Original peer content\n")
    git(repo, "add", "peer.txt")
    with monkeypatch.context() as authored:
        authored.setenv("GIT_AUTHOR_NAME", "Wrong")
        authored.setenv("GIT_AUTHOR_EMAIL", "wrong@example.invalid")
        git(repo, "commit", "-S", "-m", f"fix: legacy peer prefix\n\n{TRAILER}")
    original = git(repo, "rev-parse", "HEAD")
    git(candidate, "reset", "--hard", original)
    git(repo, "update-ref", "refs/heads/main", original, initial)
    first = repair_fixture_history(
        repo,
        tmp_path / "first-original.bundle",
        corrections={
            original: {
                "author": {
                    "expected": {"name": "Wrong", "email": "wrong@example.invalid"},
                    "replacement": {"name": "ETHOS Test", "email": "test@example.invalid"},
                }
            }
        },
    )
    (repo / "forward.txt").write_text("Forward content before the second repair\n")
    if independent:
        write_release_mirror(repo, "independent")
    git(repo, "add", ".ethos/release.toml", "forward.txt")
    git(repo, "commit", "-S", "-m", "fix: forward before second repair")
    before_second = git(repo, "rev-parse", "HEAD")
    git(candidate, "reset", "--hard", before_second)
    if not independent:
        git(repo, "update-ref", "refs/heads/main", before_second, first)
    second = repair_fixture_history(
        repo,
        tmp_path / "second-original.bundle",
        corrections={first: {"remove_attribution_trailers": [TRAILER]}},
    )
    assert is_ancestor(repo, first, before_second)
    assert not is_ancestor(repo, first, second)
    return repo, original, first, second


@pytest.mark.parametrize("case", ["valid", "subject", "unsigned"])
def test_original_peer_prefix_survives_consecutive_repairs(tmp_path, monkeypatch, case):
    """Only final-tip descendants face current policy; repair does not excuse new violations."""
    repo, original, _first, second = _consecutive_repairs(tmp_path, monkeypatch)
    head = git(
        repo,
        "commit-tree",
        *(("-S",) if case != "unsigned" else ()),
        f"{second}^{{tree}}",
        "-p",
        second,
        "-m",
        "invalid final forward" if case == "subject" else "fix: final forward",
    )
    before = git(repo, "show-ref")
    relation = repaired_object_provenance(repo, old=original, new=head)
    assert relation is not None
    mapping = relation["mapping"]
    assert isinstance(mapping, dict)
    assert mapping[original] == git(repo, "rev-parse", f"{second}^")
    assert relation["new"] == second
    exact = commit_range_admission_report(
        repo,
        target_ref="refs/heads/dev",
        proposed_head=second,
        remote_head=original,
        remote_name="origin",
    )
    assert exact["verdict"] == "pass", exact
    assert exact["repair_attestations"] == relation["attestation_ids"]
    contribution = accepted_contribution(repo, original, head)
    assert contribution["verdict"] == "pass", contribution
    assert contribution["replacement"] == mapping[original]
    assert contribution["attestation_ids"] == relation["attestation_ids"]
    report = commit_range_admission_report(
        repo,
        target_ref="refs/heads/dev",
        proposed_head=head,
        remote_head=original,
        remote_name="origin",
    )
    valid = case == "valid"
    assert report["verdict"] == ("pass" if valid else "block"), report
    assert report["integration_baseline"] == second
    assert report["revisions"] == [head]
    assert report["remote_head"] == original
    violations = report["violations"]
    assert isinstance(violations, list)
    assert {item["commit"] for item in violations} == (set() if valid else {head})
    cli = (run_ethos if valid else run_ethos_blocked)(
        "hook",
        "commit-range",
        "--target-ref",
        "refs/heads/dev",
        "--proposed-head",
        head,
        "--remote-head",
        original,
        "--remote",
        "origin",
        "--json",
        cwd=repo,
    )
    assert cli["verdict"] == report["verdict"], cli
    witnesses = report["repair_attestations"]
    assert isinstance(witnesses, list)
    assert len(witnesses) == 2
    if valid:
        peer = tmp_path / "peer.git"
        git(tmp_path, "init", "--bare", str(peer))
        git(repo, "push", str(peer), f"{original}:refs/heads/dev")
        effect, observations, gaps = observe_remote_publication_effect(
            root=repo,
            source_ref=head,
            target_refs=("refs/heads/dev",),
            remotes={"peer": str(peer)},
            ref_admissions={
                "refs/heads/dev": {"ref_kind": "branch", "remote_mutation_allowed": True}
            },
        )
        assert not gaps, gaps
        assert effect is not None
        assert effect.source.object_oid == head
        assert len(effect.targets) == len(observations) == 1
        assert {
            (update.expected, update.desired)
            for target in effect.targets
            for update in target.updates
        } == {(original, head)}
        assert git(peer, "rev-parse", "dev") == original
    assert git(repo, "show-ref") == before


@pytest.mark.parametrize("case", ["tip", "forward", "unsigned", "excluded_ref"])
def test_new_proposal_keeps_completed_baseline_ref_provenance(tmp_path, monkeypatch, case):
    """Creation uses its trusted source ref, never a repair of the absent destination."""
    repo, original, _first, second = _consecutive_repairs(
        tmp_path, monkeypatch, independent=case == "excluded_ref"
    )
    head = (
        second
        if case == "tip"
        else git(
            repo,
            "commit-tree",
            *(("-S",) if case != "unsigned" else ()),
            f"{second}^{{tree}}",
            "-p",
            second,
            "-m",
            "fix: new proposal forward source",
        )
    )
    baseline_ref = (
        "refs/remotes/origin/main" if case == "excluded_ref" else "refs/remotes/origin/dev"
    )
    git(repo, "update-ref", baseline_ref, original)
    native_zero = "0" * len(head)
    before = git(repo, "show-ref")
    report = commit_range_admission_report(
        repo,
        target_ref="refs/heads/proposal/repaired-baseline",
        proposed_head=head,
        remote_head=native_zero,
        remote_name="origin",
        trusted_baseline=baseline_ref if case == "excluded_ref" else "",
    )
    valid = case in {"tip", "forward"}
    assert report["verdict"] == ("pass" if valid else "block"), report
    assert report["remote_head"] == native_zero
    assert report["update_kind"] == "create"
    if valid or case == "unsigned":
        assert report["baseline_commit"] == original
        assert report["baseline_ref"] == baseline_ref
        assert report["integration_baseline"] == second
        assert report["revisions"] == ([] if case == "tip" else [head])
        assert len(report["repair_attestations"]) == 2
        assert {item["commit"] for item in report["violations"]} == (
            {head} if case == "unsigned" else set()
        )
        cli = (run_ethos if valid else run_ethos_blocked)(
            "hook",
            "commit-range",
            "--target-ref",
            "refs/heads/proposal/repaired-baseline",
            "--proposed-head",
            head,
            "--remote-head",
            native_zero,
            "--remote",
            "origin",
            "--json",
            cwd=repo,
        )
        assert cli["verdict"] == report["verdict"], cli
    else:
        assert report["required_gaps"] == [
            f"commit_range_trusted_baseline_not_ancestor:{original}:{head}"
        ]
    assert git(repo, "show-ref") == before


@pytest.mark.parametrize(
    "case", ["missing_result", "missing_effect", "ambiguous", "tampered", "revoked_trust"]
)
def test_repair_chain_requires_each_completed_predecessor(tmp_path, monkeypatch, case):
    """A later valid repair cannot invent a missing earlier object's provenance."""
    repo, original, first, second = _consecutive_repairs(tmp_path, monkeypatch)
    selected, records = read_attestation_set(repo)
    predecessor = next(
        item
        for item in records
        if item.predicate == RESULT and item.payload.body["replacement"] == first
    )
    if case == "missing_result":
        git(repo, "update-ref", "-d", ATTESTATION_SET_REF, selected)
        record_attestations(repo, tuple(item for item in records if item.id != predecessor.id))
    elif case == "missing_effect":
        records = tuple(
            item
            for item in records
            if not (
                item.predicate == "effect:git-ref-update"
                and item.plan_digest == predecessor.plan_digest
            )
        )
    elif case == "ambiguous":
        records = (*records, predecessor)
    elif case == "tampered":
        records = tuple(
            item.model_copy(update={"plan_digest": "0" * 64}) if item.id == predecessor.id else item
            for item in records
        )
    else:
        (tmp_path / "trust/allowed-signers").write_text("")
    if case != "missing_result":
        monkeypatch.setattr(signature, "read_attestation_set", lambda _root: (selected, records))
    before = git(repo, "show-ref")
    if case in {"missing_result", "missing_effect"}:
        assert (
            repaired_peer_ref_provenance(repo, ref="refs/heads/dev", old=original, new=second)
            is None
        )
    else:
        error = (
            "history_repair_signature_untrusted" if case == "revoked_trust" else "signature_repair_"
        )
        with pytest.raises(ValueError, match=error):
            repaired_peer_ref_provenance(repo, ref="refs/heads/dev", old=original, new=second)
    assert git(repo, "show-ref") == before


def test_repair_chain_keeps_only_refs_named_at_every_step(tmp_path, monkeypatch):
    """A release ref excluded by the successor cannot inherit the predecessor's authority."""
    repo, original, _first, second = _consecutive_repairs(tmp_path, monkeypatch, independent=True)
    before = git(repo, "show-ref")
    assert repaired_peer_ref_provenance(repo, ref="refs/heads/dev", old=original, new=second)
    assert (
        repaired_peer_ref_provenance(repo, ref="refs/heads/main", old=original, new=second) is None
    )
    assert git(repo, "show-ref") == before
