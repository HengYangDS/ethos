"""Rebuild readiness reports by count and fixed gap and refuses what an apply could not carry."""

from __future__ import annotations

import json
import subprocess
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.commit.rebuild.readiness as readiness
from ethos.repository.paradigm.peer_identity import marker_image
from ethos.repository.paradigm.peer_identity import rebuild_image
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.private_addresses import ipv4
from tests.support.rebuild import F1
from tests.support.rebuild import H1
from tests.support.rebuild import KEY_TEXT
from tests.support.rebuild import MAIN
from tests.support.rebuild import RECORD
from tests.support.rebuild import digest
from tests.support.rebuild import entry
from tests.support.rebuild import land_record
from tests.support.rebuild import peer_history
from tests.support.rebuild import record

if TYPE_CHECKING:
    from pathlib import Path

RETAINED = f"jobs https://{H1}/api/v4/projects/7/jobs\n"
NOTE = "openspec/changes/history-rebuild-map/notes.md"
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def _keyed(oid: str) -> str:
    return f'{{ digest = "{digest(rebuild_image("oid", oid))}" }}'


def _declared(ref: str, disposition: str, oid: str, gitlab: str = '"absent"') -> str:
    peers = f'{{ gitlab = {gitlab}, github = "absent" }}'
    return (
        f'\n[refs."{ref}"]\ndisposition = "{disposition}"\nold = {_keyed(oid)}\npeers = {peers}\n'
    )


def _land(repo: Path, origin: str, *, push: bool = True, refs: str = "", **edits: str) -> str:
    """Land the record over `origin`, hold main at the accepted head and publish both to gitlab."""
    fields = {
        "dev": '{ gitlab = "old", github = "absent" }',
        "hosts": entry(marker_image("host", H1), origin, count=2),
        "retain": '"api/v4/projects"',
        "refs": MAIN + refs,
    } | edits
    message = f"docs: declare the rebuild after {origin[:10]}"
    old = land_record(repo, record(origin, **fields), message)
    git(repo, "branch", "-f", "main", old)
    if push:
        git(repo, "push", "-q", "--no-verify", "gitlab", "dev", "main")
    return old


def _read(repo: Path) -> dict[str, object]:
    return readiness.rebuild_readiness(repo, record=RECORD, key=KEY_TEXT)


def test_readiness_reports_by_count_and_index_and_writes_nothing(tmp_path: Path) -> None:
    """Counts by entry, retained totals, quotes by kind and review heads; keyed names resolve."""
    repo, base = peer_history(tmp_path, extra=RETAINED, bare=True)
    root = git(repo, "rev-list", "--max-parents=0", "HEAD")
    git(repo, "tag", "v0", root)
    git(repo, "push", "-q", "--no-verify", "gitlab", "v0", f"{base}:refs/merge-requests/1/head")
    github = tmp_path / "github.git"
    stray = git(
        github,
        "-c",
        "user.name=P",
        "-c",
        "user.email=p@example.com",
        "commit-tree",
        EMPTY_TREE,
        "-m",
        "x",
    )
    git(github, "update-ref", "refs/pull/2/head", stray)
    tag = _declared("refs/tags/v0", "retire", root, gitlab=_keyed(root))
    _land(repo, base, refs=tag, base=_keyed(base))
    before = (git(repo, "for-each-ref"), git(repo, "status", "--porcelain"))

    report = _read(repo)

    assert (report["state"], report["required_gaps"]) == ("ready_to_rebuild", []), report
    assert report["counts"] == {"spans": [1], "hosts": [2], "paths": [1]}
    assert report["retained"] == [1]
    assert report["quoted_ids"] == {"commit": {"commit": 1}}
    assert report["review_refs"] == {
        "gitlab": {"affected": 1, "unknown": 0},
        "github": {"affected": 0, "unknown": 1},
    }
    assert (git(repo, "for-each-ref"), git(repo, "status", "--porcelain")) == before
    assert not any(value in json.dumps(report) for value in (H1, F1, "api/v4"))


def _case(repo: Path, base: str, case: str) -> dict[str, str]:
    """Change the repository or the record so that exactly one refusal applies."""
    root = git(repo, "rev-list", "--max-parents=0", "HEAD")
    note = {
        "span": f"clone https://{H1}:8443/{F1}\n",
        "after-host": f"ssh git@{H1}:other/x\n",
        "feed": "mirror old.example.invalid\n",
        "id": "CI_PROJECT_ID=123456789 and projects/123456789\n",
    }
    if case in note:
        noted = commit_fixture_file(repo, NOTE, note[case], "docs: note the peer")
    if case == "feed":
        git(repo, "config", "--add", "remote.gitlab.forgeFormer", "host=old.example.invalid")
    if case == "id":
        image = rebuild_image("id", "id.ci-project-id", "123456789")
        witness = f'{{ object = "{noted}", path = "{NOTE}", n = 1 }}'
        named = f'contexts = ["id.ci-project-id"], digests = ["{digest(image)}"], count = 1'
        ids = f"{{ {named}, witness = {witness} }}"
        return {"ids": ids}
    if case == "header":
        git(repo, "commit", "-q", "--allow-empty", "--author", f"Bot <bot@{H1}>", "-m", "chore: x")
    if case == "tagger":
        tagged = f"object {root}\ntype commit\ntag v0\ntagger Bot <bot@{H1}> 0 +0000\n\nrelease\n"
        made = subprocess.run(
            ("git", "mktag"), check=True, cwd=repo, input=tagged, capture_output=True, text=True
        )
        git(repo, "update-ref", "refs/tags/v0", made.stdout.strip())
    if case == "tree-name":
        commit_fixture_file(
            repo, f"openspec/changes/history-rebuild-map/{H1}/x.md", "x\n", "docs: x"
        )
    if case in {"ref", "keep-unpublishable"}:
        git(repo, "branch", "topic", root)
    if case in {"keep-affected", "retag-unreleased", "private"}:
        message = f"release {ipv4(10, 0, 0, 1)}" if case == "private" else "release"
        git(repo, "tag", "-a", "v0", "-m", message, base)
    if case in {"keep-own-message", "retag-target"}:
        git(repo, "tag", "-a", "v0", "-m", f"release {F1}", root)
    if case == "retag-of-tag":
        git(repo, "tag", "-a", "v1", "-m", "release", base)
        git(repo, "tag", "-a", "v0", "-m", "again", "v1")
    if case in {"notes", "lightweight"}:
        git(repo, *("notes", "add", "-m", "x", base) if case == "notes" else ("tag", "v0", base))
    declared = {
        "tagger": ("refs/tags/v0", "retire"),
        "keep-unpublishable": ("refs/heads/topic", "keep"),
        "keep-affected": ("refs/tags/v0", "keep"),
        "keep-own-message": ("refs/tags/v0", "keep"),
        "retag-target": ("refs/tags/v0", "retag"),
        "retag-unreleased": ("refs/tags/v0", "retag"),
        "private": ("refs/tags/v0", "retag"),
        "retag-of-tag": ("refs/tags/v0", "retag"),
        "notes": ("refs/notes/commits", "keep"),
        "lightweight": ("refs/tags/v0", "retag"),
    }
    if case not in declared:
        return {}
    ref, disposition = declared[case]
    extra = (
        _declared("refs/tags/v1", "retire", git(repo, "rev-parse", "v1"))
        if case == "retag-of-tag"
        else ""
    )
    return {"refs": _declared(ref, disposition, git(repo, "rev-parse", ref)) + extra}


@pytest.mark.parametrize(
    ("case", "gap"),
    [
        ("span", "rebuild_undeclared:span"),
        ("after-host", "rebuild_undeclared_after_host"),
        ("feed", "rebuild_feed_uncovered:host"),
        ("id", "rebuild_undeclared:id"),
        ("header", "rebuild_header_item"),
        ("tagger", "rebuild_header_item"),
        ("tree-name", "rebuild_tree_name_item"),
        ("ref", "rebuild_ref_undeclared:refs/heads/topic"),
        ("peer", "rebuild_peer_state:refs/heads/dev:gitlab"),
        ("main", "rebuild_main_not_dev"),
        ("keep-affected", "rebuild_keep_affected:refs/tags/v0"),
        ("keep-own-message", "rebuild_keep_affected:refs/tags/v0"),
        ("keep-unpublishable", "rebuild_keep_unpublishable:refs/heads/topic"),
        ("retag-target", "rebuild_retag_target_unaffected:refs/tags/v0:retire"),
        ("retag-of-tag", "rebuild_retag_of_tag:refs/tags/v0:retire"),
        ("notes", "rebuild_disposition_refused:refs/notes/commits"),
        ("lightweight", "rebuild_disposition_refused:refs/tags/v0"),
        ("retag-unreleased", "rebuild_retag_unreleased:refs/tags/v0"),
        ("private", "rebuild_tag_message_private:refs/tags/v0"),
    ],
)
def test_readiness_refuses_what_an_apply_could_not_carry(
    tmp_path: Path, case: str, gap: str
) -> None:
    """Each refusal is a fixed gap that names a ref or a form, never a value."""
    repo, base = peer_history(tmp_path, extra=RETAINED, bare=True)
    edits = _case(repo, base, case)
    old = _land(repo, base, push=case != "peer", **edits)
    if case == "main":
        git(repo, "branch", "-f", "main", base)

    report = _read(repo)

    assert gap in report["required_gaps"], report["required_gaps"]
    assert report["state"] == "blocked"
    assert old in str(report["head"])
    assert not any(value in json.dumps(report) for value in (H1, F1, "123456789"))


@pytest.mark.parametrize(
    "case", ["shallow", "grafts", "worktree", "private", "unread", "stray", "ethos"]
)
def test_readiness_refuses_history_and_peers_it_cannot_see_whole(tmp_path: Path, case: str) -> None:
    """Hidden history, an unread peer and a peer's undeclared or `refs/ethos/` ref refuse."""
    repo, base = peer_history(tmp_path, extra=RETAINED, bare=True)
    old = _land(repo, base)
    common = tmp_path / "repo/.git"
    if case in {"shallow", "grafts"}:
        (common / "info").mkdir(exist_ok=True)
        (common / ("shallow" if case == "shallow" else "info/grafts")).write_text(f"{old}\n")
    if case == "worktree":
        git(repo, "worktree", "add", "-q", "--detach", str(tmp_path / "detached"), old)
    if case == "private":
        git(repo, "worktree", "add", "-q", "-b", "side", str(tmp_path / "side"), old)
        git(tmp_path / "side", "update-ref", "refs/worktree/held", old)
    if case == "unread":
        git(repo, "remote", "set-url", "gitlab", str(tmp_path / "absent.git"))
    if case in {"stray", "ethos"}:
        ref = "refs/heads/stray" if case == "stray" else "refs/ethos/attestations-set"
        git(repo, "push", "-q", "--no-verify", "gitlab", f"{base}:{ref}")

    gaps = _read(repo)["required_gaps"]

    assert {
        "shallow": "rebuild_history_hidden:shallow",
        "grafts": "rebuild_history_hidden:grafts",
        "worktree": "rebuild_history_hidden:worktree",
        "private": "rebuild_history_hidden:worktree",
        "unread": "rebuild_peer_unread:gitlab",
        "stray": "rebuild_peer_ref_undeclared:gitlab:refs/heads/stray",
        "ethos": "rebuild_peer_ethos_ref:gitlab",
    }[case] in gaps


@pytest.mark.parametrize(
    ("case", "gaps"),
    [
        ("qualified", []),
        ("moved", ["rebuild_retag_unqualified:refs/tags/v0"]),
        ("unmapped", ["rebuild_retag_base_unmapped:refs/tags/v0"]),
    ],
)
def test_a_retag_publishes_only_on_its_verified_original_qualification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str, gaps: list[str]
) -> None:
    """The release record of the original tag qualifies it; today's CHANGELOG is never read."""
    repo, base = peer_history(tmp_path, extra=RETAINED, bare=True)
    git(repo, "tag", "-a", "v0", "-m", "release", base)
    _land(repo, base, refs=_declared("refs/tags/v0", "retag", git(repo, "rev-parse", "v0")))
    request = {"release_request": {"base": "f" * 40 if case == "unmapped" else ""}}
    facts = {"head": base if case != "moved" else "e" * 40, "values": request}
    plan = SimpleNamespace(facts=facts, prior_attestations={"proof": {"id": "proof-1"}})
    monkeypatch.setattr(readiness, "release_provenance", lambda *_args, **_kwargs: plan)

    assert _read(repo)["required_gaps"] == gaps
