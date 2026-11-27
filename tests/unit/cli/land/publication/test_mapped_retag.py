"""A release tag on a repaired commit is re-created on its replacement, as its original."""

from __future__ import annotations

import json
import subprocess
from contextlib import nullcontext
from contextlib import redirect_stderr
from io import StringIO
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

import ethos.adapters.mutation.accepted.retag as retag
import ethos.adapters.mutation.proof_admission as proof_admission
import ethos.adapters.repo.release as release
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.hook.protocol import execute_hook
from ethos.contracts.outcome import OutcomeError
from ethos.contracts.outcome import refusal
from ethos.contracts.proof.plan import PROOF_PREDICATES
from tests.support.ethos_cli_runner import run_ethos
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.signature import repair_fixture_history
from tests.support.signature import signature_repository
from tests.unit.cli.land.publication.support import accepted_release_fixture
from tests.unit.cli.land.publication.support import apply_receipt
from tests.unit.cli.land.publication.support import branch_publication
from tests.unit.cli.land.publication.support import later_policy
from tests.unit.cli.land.publication.support import publication_peers
from tests.unit.cli.land.publication.support import release_cli

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.adapters.mutation.accepted.retag import RetagReport
    from ethos.contracts.plan import TransitionPlan
    from ethos.contracts.semantic import Attestation


def _repaired_with_tags(tmp_path: Path) -> tuple[Path, str, str, str, str]:
    """Sign tags v1.0.0 on the replaced commit and v0.9.0 on its unmapped root."""
    repo, old, _candidate = signature_repository(tmp_path, coupled=True)
    root = git(repo, "rev-list", "--max-parents=0", old)
    for name, target in (("v1.0.0", old), ("v0.9.0", root)):
        git(repo, "tag", "-s", "-m", f"Release {name}", name, target)
    original = git(repo, "rev-parse", "refs/tags/v1.0.0")
    replacement = repair_fixture_history(
        repo,
        tmp_path / "original.bundle",
        corrections={old: {"resign": True}},
        refs=("refs/heads/dev", "refs/tags/v1.0.0"),
    )
    return repo, old, replacement, original, root


def _tag_body(repo: Path, oid: str) -> tuple[list[str], str]:
    """Return a tag's header lines without its object line, and its message without signature."""
    raw = git(repo, "cat-file", "tag", oid)
    header, _, body = raw.partition("\n\n")
    message = body.split("-----BEGIN SSH SIGNATURE-----", 1)[0]
    return [line for line in header.splitlines() if not line.startswith("object ")], message


def _applied(repo: Path, tags: tuple[str, ...], preview: RetagReport) -> RetagReport:
    """Apply what the preview planned, under its plan digest."""
    digest = preview["data"]["plan_digest"]
    return retag.mapped_retag(
        repo, tags=tags, apply=True, authorized=True, expect_plan_digest=digest
    )


def test_a_pruned_tag_is_recreated_from_the_repair_bundle(tmp_path: Path) -> None:
    """Only the target and signature change; one receipt binds both objects and the mapping.

    The original was pruned locally, so `land --retag` restores it from the repair's bundle.
    """
    repo, old, replacement, original, _root = _repaired_with_tags(tmp_path)
    git(repo, "tag", "-d", "v1.0.0")
    git(repo, "prune", "--expire=now")
    present = subprocess.run(("git", "-C", str(repo), "cat-file", "-e", original), check=False)
    assert present.returncode != 0
    request = ("land", "--retag=v1.0.0", f"--original-tag=v1.0.0={original}", "--json")
    preview = run_ethos(*request, cwd=repo)
    assert (preview["verdict"], preview["state"]) == ("pass", "ready_to_retag"), preview
    digest = preview["data"]["plan_digest"]
    assert f"--expect-plan-digest={digest}" in preview["next_action"]
    applied = run_ethos(
        *request, "--apply", "--authorize", f"--expect-plan-digest={digest}", cwd=repo
    )
    assert (applied["verdict"], applied["state"]) == ("pass", "retagged"), applied
    recreated = git(repo, "rev-parse", "refs/tags/v1.0.0")
    assert recreated != original
    assert git(repo, "rev-parse", "refs/tags/v1.0.0^{}") == replacement
    assert git(repo, "verify-tag", "refs/tags/v1.0.0") == ""
    assert _tag_body(repo, recreated) == _tag_body(repo, original)
    (receipt,) = [
        item
        for item in read_attestation_set(repo)[1]
        if item.predicate == retag.RETAG_PREDICATE
        and item.subject == f"git:annotated-tag:{recreated}"
    ]
    body = receipt.payload.body
    assert (body["original_tag"], body["mapped_target"], body["original_target"]) == (
        original,
        replacement,
        old,
    )
    assert body["mapping_attestation_id"]


TWO_TAGS = ("v1.0.0", "v1.1.0")


def _two_repaired_tags(tmp_path: Path) -> tuple[Path, list[str], str]:
    """Tag the replaced commit and the head above it, then repair both onto a re-signed line."""
    repo, old, _candidate = signature_repository(tmp_path)
    second = commit_fixture_file(repo, "second.txt", "second\n", "docs: add a second file")
    for name, target in zip(TWO_TAGS, (old, second), strict=True):
        git(repo, "tag", "-s", "-m", f"Release {name}", name, target)
    originals = [git(repo, "rev-parse", f"refs/tags/{name}") for name in TWO_TAGS]
    head = repair_fixture_history(
        repo,
        tmp_path / "original.bundle",
        corrections={old: {"resign": True}},
        refs=("refs/heads/dev", *(f"refs/tags/{name}" for name in TWO_TAGS)),
    )
    return repo, originals, head


def test_two_tags_on_different_commits_are_recreated_in_one_run(tmp_path: Path) -> None:
    """One run re-creates two tags on different commits below the checkout, under one plan digest.

    Each effect moves one tag ref by exact compare-and-swap; the checkout it is asked from stays
    where it is and is the plan's pre-state.
    """
    repo, originals, head = _two_repaired_tags(tmp_path)
    later = commit_fixture_file(repo, "later.txt", "later\n", "docs: add a later file")
    preview = retag.mapped_retag(repo, tags=TWO_TAGS)
    assert preview["verdict"] == "pass", preview
    applied = _applied(repo, TWO_TAGS, preview)
    assert (applied["verdict"], applied["state"]) == ("pass", "retagged"), applied
    assert git(repo, "rev-parse", "refs/tags/v1.0.0^{}") == git(repo, "rev-parse", f"{head}~1")
    assert git(repo, "rev-parse", "refs/tags/v1.1.0^{}") == head
    assert [git(repo, "rev-parse", f"refs/tags/{name}") for name in TWO_TAGS] != originals
    assert all(git(repo, "verify-tag", f"refs/tags/{name}") == "" for name in TWO_TAGS)
    assert git(repo, "rev-parse", "HEAD") == later


@pytest.mark.parametrize(
    ("failure", "verdict"),
    [("moved-checkout", "block"), ("unknown", "unknown"), ("after-the-move", "block")],
)
def test_a_batch_stops_only_where_a_refusal_left_its_tag_unmoved(
    tmp_path: Path, failure: str, verdict: str
) -> None:
    """Each tag states the head the batch was asked from, so a move between two tags refuses.

    That refusal leaves the next tag where it stood, so the batch reports it and keeps the moved
    tag's receipt. A failure of unknown outcome, or one after its tag moved, keeps its verdict.
    """
    repo, originals, _head = _two_repaired_tags(tmp_path)
    preview = retag.mapped_retag(repo, tags=TWO_TAGS)
    execute, plans = retag.execute_git_effect, []

    def second_fails(root: Path, plan: TransitionPlan, **options: str) -> object:
        plans.append(plan)
        if len(plans) == 2 and failure == "moved-checkout":
            git(repo, "switch", "--detach", "HEAD~1")
        if len(plans) == 1 or failure == "moved-checkout":
            return execute(root, plan, **options)
        if failure == "after-the-move":
            execute(root, plan, **options)
        rejected = "git_effect_cas_rejected"
        raise refusal(rejected, verdict=verdict)

    with patch.object(retag, "execute_git_effect", second_fails):
        if failure == "moved-checkout":
            stopped = _applied(repo, TWO_TAGS, preview)
        else:
            with pytest.raises(OutcomeError) as raised:
                _applied(repo, TWO_TAGS, preview)
    assert git(repo, "rev-parse", "refs/tags/v1.0.0") != originals[0]
    if failure != "moved-checkout":
        assert raised.value.outcome.verdict == verdict
        return
    blocked = ("block", "blocked", ["release_retag_refused:v1.1.0"])
    assert (stopped["verdict"], stopped["state"], stopped["required_gaps"]) == blocked, stopped
    assert stopped["data"]["refused"] == {"v1.1.0": ["git_effect_plan_prestate_stale"]}
    (receipt,) = [item["receipt"] for item in stopped["data"]["planned"].values()]
    assert receipt in {item.id for item in read_attestation_set(repo)[1]}
    assert git(repo, "rev-parse", "refs/tags/v1.1.0") == originals[1]


@pytest.mark.parametrize("place", ["unborn", "lane", "detached-elsewhere", "detached-at-tag"])
def test_a_retag_is_asked_from_the_repaired_line(tmp_path: Path, place: str) -> None:
    """A checkout that is neither at the tag's commit nor at the accepted head is refused by name.

    The preview refuses as the apply would, and no tag moves; the tag's own commit still serves.
    """
    repo, old, replacement, original, _root = _repaired_with_tags(tmp_path)
    commit_fixture_file(repo, "later.txt", "later\n", "docs: add a later file")
    if place == "unborn":
        git(repo, "checkout", "--orphan", "empty")
    elif place == "lane":
        git(repo, "switch", "-c", "work/elsewhere")
        commit_fixture_file(repo, "lane.txt", "lane\n", "docs: add a lane file")
    elif place == "detached-elsewhere":
        git(repo, "switch", "--detach", old)
    else:
        git(repo, "switch", "--detach", replacement)
    preview = retag.mapped_retag(repo, tags=("v1.0.0",))
    if place == "detached-at-tag":
        assert (preview["verdict"], preview["state"]) == ("pass", "ready_to_retag"), preview
        return
    assert preview["verdict"] == "block", preview
    assert preview["data"]["refused"] == {"v1.0.0": ["release_retag_checkout_unrelated"]}
    applied = _applied(repo, ("v1.0.0",), preview)
    assert applied["verdict"] == "block", applied
    assert applied["data"]["refused"] == {"v1.0.0": ["release_retag_checkout_unrelated"]}
    assert git(repo, "rev-parse", "refs/tags/v1.0.0") == original


@pytest.mark.parametrize(
    ("case", "gap"),
    [
        ("unmapped", "release_retag_target_not_mapped"),
        ("unverified", "release_retag_mapping_unverified"),
        ("missing", "release_retag_original_missing"),
        ("occupied", "release_retag_name_occupied"),
        ("stale", "release_retag_plan_digest_mismatch"),
    ],
)
def test_a_retag_refuses_by_name(tmp_path: Path, case: str, gap: str) -> None:
    """Every tag in a batch is judged on its own and refused by name, never skipped."""
    repo, _old, _replacement, original, root = _repaired_with_tags(tmp_path)
    tags, originals = ("v1.0.0",), {"v1.0.0": original}
    if case == "unmapped":
        tags, originals = ("v1.0.0", "v0.9.0"), {"v1.0.0": original}
        git(repo, "tag", "-d", "v1.0.0")
    elif case == "missing":
        # A bundle that no longer hashes to its recorded digest restores nothing, even this tag.
        bundle = str(tmp_path / "original.bundle")
        git(
            repo,
            "bundle",
            "create",
            bundle,
            "refs/heads/dev",
            "refs/tags/v1.0.0",
            "refs/tags/v0.9.0",
        )
        git(repo, "tag", "-d", "v1.0.0")
        git(repo, "prune", "--expire=now")
    elif case == "occupied":
        git(repo, "tag", "-f", "-s", "-m", "Release v1.0.0", "v1.0.0", root)
    else:
        git(repo, "tag", "-d", "v1.0.0")
    unverified = ValueError("signature_repair_plan_mismatch")
    broken = patch.object(retag, "repaired_object_provenance", side_effect=unverified)
    with broken if case == "unverified" else nullcontext():
        report = retag.mapped_retag(
            repo,
            tags=tags,
            original_tags=originals,
            apply=case == "stale",
            authorized=True,
            expect_plan_digest="0" * 64 if case == "stale" else "",
        )
    assert report["verdict"] == "block", report
    required, refused = report["required_gaps"], report["data"]["refused"]
    assert gap in required or any(gap in gaps for gaps in refused.values()), report
    if case == "unmapped":
        assert set(refused) == {"v0.9.0"}, refused
    unchanged = {"occupied": git(repo, "rev-parse", "refs/tags/v0.9.0^{}")}.get(case, "")
    assert git(repo, "for-each-ref", "--format=%(*objectname)", "refs/tags/v1.0.0") == unchanged


def test_an_untrusted_signer_refuses(tmp_path: Path) -> None:
    """The recreated object must verify under the trust anchor in force before any ref moves."""
    repo, _old, _replacement, original, _root = _repaired_with_tags(tmp_path)
    git(repo, "tag", "-d", "v1.0.0")
    stranger = tmp_path / "stranger"
    git(repo, "config", "--local", "user.signingkey", str(stranger) + ".pub")
    generate = ("ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(stranger))
    subprocess.run(generate, check=True, capture_output=True, timeout=15)
    report = retag.mapped_retag(repo, tags=("v1.0.0",), original_tags={"v1.0.0": original})
    refused = report["data"]["refused"]
    assert report["verdict"] == "block", report
    assert "release_retag_signer_untrusted" in refused["v1.0.0"], report
    assert git(repo, "for-each-ref", "--format=%(objectname)", "refs/tags/v1.0.0") == ""


def _prepared(repo: Path, old: str, new: str) -> list[str]:
    """Return the gaps the reference-transaction hook reports for one prepared tag move."""
    stream = StringIO()
    with redirect_stderr(stream):
        execute_hook(
            repo,
            "reference-transaction",
            ("prepared",),
            stdin=StringIO(f"{old} {new} refs/tags/v1.2.3\n"),
        )
    return json.loads(stream.getvalue())["required_gaps"] if stream.getvalue() else []


def _without_receipts(root: Path) -> tuple[str, tuple[Attestation, ...]]:
    selected, members = read_attestation_set(root)
    return selected, tuple(item for item in members if item.predicate != retag.RETAG_PREDICATE)


def test_a_recreated_tag_publishes_on_its_original_qualification(tmp_path: Path) -> None:
    """Under a later policy, the receipt carries the original release record's embedded proof.

    Once the tag moves off the original commit, that commit's proof member ends; the release
    record still qualifies the re-created tag, and without the receipt nothing does.
    """
    repo, _main, old, head = accepted_release_fixture(tmp_path, release_mirror="accepted_ff")
    assert release_cli(repo, head, head, "--apply", "--authorize")["verdict"] == "pass"
    original = git(repo, "rev-parse", "refs/tags/v1.2.3")
    legacy = git(repo, "rev-parse", f"{head}^")
    repair_fixture_history(
        repo, tmp_path / "original.bundle", corrections={legacy: {"resign": True}}
    )
    replacement = git(repo, "rev-parse", "HEAD")
    preview = retag.mapped_retag(repo, tags=("v1.2.3",))
    assert preview["verdict"] == "pass", preview
    planned = preview["data"]["planned"]["v1.2.3"]["recreated"]
    # The hook takes only the planned move to its intent; any other move stays immutable.
    assert _prepared(repo, original, planned) == ["release_ref_move_no_ref_intent"]
    assert _prepared(repo, original, head) != ["release_ref_move_no_ref_intent"]
    assert _prepared(repo, planned, original) != ["release_ref_move_no_ref_intent"]
    applied = _applied(repo, ("v1.2.3",), preview)
    assert applied["verdict"] == "pass", applied
    assert git(repo, "rev-parse", "refs/tags/v1.2.3^{}") == replacement != head
    proofs = {i.subject for i in read_attestation_set(repo)[1] if i.predicate in PROOF_PREDICATES}
    assert f"git:commit:{head}" not in proofs
    peers = publication_peers(repo, tmp_path, f"{old}:refs/heads/main")
    command = (repo, replacement, "--peer", "github")
    with patch.object(proof_admission, "resolve_proof_policies", later_policy):
        with patch.object(release, "read_attestation_set", _without_receipts):
            blocked = branch_publication(*command, target_ref="refs/tags/v1.2.3", blocked=True)
        published = branch_publication(*command, target_ref="refs/tags/v1.2.3")
        assert published["verdict"] == "pass", published
        result = apply_receipt(repo, published["data"]["request_receipt"], replacement)
    assert blocked["verdict"] == "block", blocked
    assert published["data"]["proof_admission"]["attestation"]["commit"] == head
    assert result["state"] == "published", result
    assert git(peers["github"], "rev-parse", "refs/tags/v1.2.3") == planned
    assert git(peers["github"], "rev-parse", "refs/tags/v1.2.3^{}") == replacement
    bound = preview["data"]["planned"]["v1.2.3"]["mapping_attestation_id"]
    forgeries = (
        {"mapping": {head: head}, "attestation_id": bound},
        {"mapping": {head: replacement}, "attestation_id": "0" * 64},
    )
    for forged in forgeries:
        unverified = patch.object(release, "repaired_object_provenance", return_value=forged)
        with unverified, pytest.raises(ValueError, match="release_retag_mapping_unverified"):
            release.mapped_release_provenance(repo, ref="refs/tags/v1.2.3", oid=planned)
