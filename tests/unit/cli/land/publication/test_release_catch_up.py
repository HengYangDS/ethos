"""A declared peer that missed a release later receives the exact attested tag."""

from __future__ import annotations

import json
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import ethos.adapters.repo.release as release_owner
from ethos.adapters.admission.publication import push_admission_report
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.hook.protocol import execute_hook
from tests.support.ethos_cli_runner import run_ethos
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.proof import seed_executed_proof
from tests.unit.cli.land.publication.support import accepted_release_fixture
from tests.unit.cli.land.publication.support import apply_receipt
from tests.unit.cli.land.publication.support import branch_publication
from tests.unit.cli.land.publication.support import publication_peers
from tests.unit.cli.land.publication.support import release_cli

TAG_REF = "refs/tags/v1.2.3"


def _pre_push(repo: Path, tag: str, remote_oid: str) -> tuple[int, list[str]]:
    """Run native pre-push for one gitlab tag update and return its gaps."""
    stream = StringIO()
    with redirect_stderr(stream):
        code = execute_hook(
            repo,
            "pre-push",
            ("gitlab",),
            stdin=StringIO(f"{TAG_REF} {tag} {TAG_REF} {remote_oid}\n"),
        )
    output = stream.getvalue()
    return code, json.loads(output)["required_gaps"] if output else []


def _released_while_gitlab_was_away(tmp_path: Path) -> tuple[Path, dict[str, Path], str, str]:
    """Publish one release to github only, then advance accepted past it."""
    repo, _main, old, head = accepted_release_fixture(tmp_path, release_mirror="accepted_ff")
    assert release_cli(repo, head, head, "--apply", "--authorize")["verdict"] == "pass"
    peers = publication_peers(repo, tmp_path, f"{old}:refs/heads/main")
    gitlab = git(repo, "remote", "get-url", "gitlab")
    git(repo, "remote", "set-url", "gitlab", str(tmp_path / "unavailable-gitlab.git"))
    preview = branch_publication(repo, head, "--peer", "github", target_ref=TAG_REF)
    assert apply_receipt(repo, preview["data"]["request_receipt"], head)["state"] == "published"
    git(repo, "remote", "set-url", "gitlab", gitlab)
    candidate = tmp_path / "repo"
    (candidate / "notes").mkdir(exist_ok=True)
    (candidate / "notes/after-release.txt").write_text(
        "accepted after the release\n", encoding="utf-8"
    )
    accepted = commit_fixture(candidate, "fix: advance accepted after the release")
    seed_executed_proof(candidate, accepted)
    run_ethos(
        "land",
        "--closeout",
        "--apply",
        "--authorize",
        "--expect-head",
        head,
        "--candidate-head",
        accepted,
        "--json",
        cwd=repo,
    )
    assert git(repo, "rev-parse", "HEAD") == git(repo, "rev-parse", "dev") == accepted
    return repo, peers, head, accepted


def test_peer_that_missed_a_release_receives_the_attested_tag(tmp_path: Path) -> None:
    """Catch-up publishes the released object once, attests it and stays idempotent."""
    repo, peers, head, accepted = _released_while_gitlab_was_away(tmp_path)
    tag = git(repo, "rev-parse", TAG_REF)
    assert git(peers["github"], "rev-parse", TAG_REF) == tag
    assert git(peers["gitlab"], "for-each-ref", "--format=%(objectname)", TAG_REF) == ""
    with (
        patch.object(
            release_owner, "release_provenance", wraps=release_owner.release_provenance
        ) as provenance,
        patch.object(
            release_owner, "accepted_release_source", wraps=release_owner.accepted_release_source
        ) as source,
    ):
        assert (
            release_owner.release_ref_subject(
                repo, ref=TAG_REF, old="0" * len(head), new=tag, allow_identical=True
            )
            == head
        )
        assert (provenance.call_count, source.call_count) == (1, 1)
        provenance.reset_mock()
        source.reset_mock()
        admitted = push_admission_report(
            root=repo,
            target_ref=TAG_REF,
            pushed_head=tag,
            remote_head="0" * len(head),
            remote_name="gitlab",
        )
        assert admitted["verdict"] == "pass", admitted
        assert (provenance.call_count, source.call_count) == (1, 1)
    assert _pre_push(repo, tag, "0" * len(head)) == (0, [])
    assert _pre_push(repo, tag, tag) == (0, [])

    preview = branch_publication(repo, accepted, "--peer", "gitlab", target_ref=TAG_REF)
    assert preview["verdict"] == "pass", preview
    assert preview["data"]["remote_effect"]["source"]["peeled_commit"] == head
    applied = apply_receipt(repo, preview["data"]["request_receipt"], accepted)
    assert (applied["verdict"], applied["state"]) == ("pass", "published"), applied
    for peer in peers.values():
        assert git(peer, "rev-parse", TAG_REF) == tag
        assert git(peer, "rev-parse", f"{TAG_REF}^{{}}") == head
    attestation_id = applied["data"]["remote_effect"]["attestation"]["id"]
    recorded = next(item for item in read_attestation_set(repo)[1] if item.id == attestation_id)
    assert (recorded.predicate, recorded.subject) == (
        "publication:remote-effect",
        f"git:annotated-tag:{tag}",
    )
    assert [target["id"] for target in recorded.payload.body["effect"]["targets"]] == ["gitlab"]

    repeated = branch_publication(repo, accepted, target_ref=TAG_REF)
    assert repeated["verdict"] == "pass", repeated
    again = apply_receipt(repo, repeated["data"]["request_receipt"], accepted)
    assert (again["verdict"], again["state"]) == ("pass", "published"), again
    assert {attempt["state"] for attempt in again["data"]["remote_effect"]["attempts"]} == {
        "already_applied"
    }


def test_catch_up_refuses_replaced_untrusted_divergent_or_unaccepted_tags(tmp_path: Path) -> None:
    """Only the attested object, still trusted and in accepted history, catches up."""
    repo, peers, head, accepted = _released_while_gitlab_was_away(tmp_path)
    tag = git(repo, "rev-parse", TAG_REF)
    zero = "0" * len(head)
    replacements = []
    for signing in (("-s", "-m", "re-signed release"), ("-a", "-m", "unsigned release")):
        git(repo, "tag", "-f", *signing, "v1.2.3", head)
        replacements.append(git(repo, "rev-parse", TAG_REF))
        code, gaps = _pre_push(repo, replacements[-1], zero)
        assert (code, "release_tag_source_untrusted" in gaps) == (1, True), gaps
    git(repo, "update-ref", TAG_REF, tag)

    git(repo, "push", "gitlab", f"{replacements[0]}:{TAG_REF}")
    code, gaps = _pre_push(repo, tag, replacements[0])
    assert (code, "release_tag_immutable" in gaps) == (1, True), gaps
    blocked = branch_publication(
        repo, accepted, "--peer", "gitlab", target_ref=TAG_REF, blocked=True
    )
    assert blocked["verdict"] == "block"
    assert git(peers["gitlab"], "rev-parse", TAG_REF) == replacements[0]
    git(peers["gitlab"], "update-ref", "-d", TAG_REF)

    anchor = Path(git(repo, "config", "--path", "--get", "gpg.ssh.allowedSignersFile"))
    trust = anchor.read_text()
    anchor.write_text("")
    try:
        code, gaps = _pre_push(repo, tag, zero)
        assert (code, "release_tag_source_untrusted" in gaps) == (1, True), gaps
    finally:
        anchor.write_text(trust)

    detached = tmp_path / "detached"
    git(repo, "worktree", "add", "--detach", str(detached), f"{head}^")
    (detached / "rewritten.txt").write_text("accepted without the release\n", encoding="utf-8")
    rewritten = commit_fixture(detached, "fix: accepted history without the release")
    git(repo, "update-ref", "refs/heads/dev", rewritten, accepted)
    code, gaps = _pre_push(repo, tag, zero)
    assert (code, "release_tag_source_untrusted" in gaps) == (1, True), gaps
    assert git(peers["gitlab"], "for-each-ref", "--format=%(objectname)", TAG_REF) == ""
