"""A rebuild's originals are walked once, so counts and witnesses agree over a whole history."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.adapters.repo.commit.rebuild.originals import original_history
from ethos.adapters.repo.commit.rebuild.originals import original_sightings
from ethos.adapters.repo.commit.rebuild.originals import reaching
from ethos.adapters.repo.git_object import tag_message
from ethos.repository.paradigm.peer_identity import Feed
from ethos.repository.paradigm.peer_identity import attributed
from ethos.repository.paradigm.peer_identity import counts
from ethos.repository.paradigm.peer_identity import marker_image
from ethos.repository.paradigm.peer_identity import occurrences
from ethos.repository.paradigm.peer_identity import rebuild_image
from ethos.repository.paradigm.peer_identity import replacement_spans
from tests.support.governed_repository import git

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.repository.paradigm.peer_identity import Witness

H1 = "forge.example.invalid"
F1 = "team/infra/tools"
FEED = Feed.of(hosts=[H1], ports=[8443, 2222], paths=[F1], ids=[123456789], citations=[f"{F1}!42"])
ENTRIES = {
    rebuild_image("id", "id.project-word", "123456789"): "id:project-word",
    marker_image("prefix", H1, "8443", F1): "span:url",
    marker_image("host", H1): "host",
    marker_image("path", path=F1): "path",
    rebuild_image("port", "8443"): "port",
    marker_image("path", path=f"{F1}!42"): "span:citation",
    rebuild_image("id", "id.aigw-ci-cache", "123456789"): "id:aigw-ci-cache",
    marker_image("host", H1, "2222"): "span:authority",
}
# Version 1's occurrence model over the history below: each entry's witnesses as (object, path, n),
# so its count. A blob kept across a rename or held at two paths is read once, at its first path.
VERSION_1 = {
    "id:project-word": [("root", "", 1)],
    "span:url": [("root", "docs/a.md", 1)],
    "host": [("root", "docs/a.md", 1), ("root", "docs/a.md", 2)],
    "path": [("root", "docs/b.md", 1), ("root", "docs/b.md", 2)],
    "port": [("side", "docs/s.md", 1)],
    "span:citation": [("merge", "", 1)],
    "id:aigw-ci-cache": [("merge", "docs/merge.md", 1)],
    "span:authority": [("tag", "", 1)],
}


def _history(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    """Build a root commit, a side branch, a gitlink, a rename, a merge that adds a file, a tag.

    The gitlink names a commit that the repository lacks, so a walk that read it would fail.
    """
    repo = tmp_path / "repo"
    git(tmp_path, "init", "-q", "-b", "main", str(repo))

    def commit(message: str, files: dict[str, str]) -> str:
        for name, text in files.items():
            (repo / name).parent.mkdir(parents=True, exist_ok=True)
            (repo / name).write_text(text, encoding="utf-8")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", message)
        return git(repo, "rev-parse", "HEAD")

    shared = f"see {F1} and {F1}\n"
    record = f"clone https://{H1}:8443/{F1}.git\nssh git@{H1}\nssh git@{H1} again\n"
    root = commit(
        "root: project 123456789",
        {"docs/a.md": record, "docs/b.md": shared, "docs/c.md": shared},
    )
    git(repo, "switch", "-q", "-c", "side")
    side = commit("side", {"docs/s.md": "listen on port 8443\n"})
    git(repo, "switch", "-q", "main")
    git(repo, "update-index", "--add", "--cacheinfo", f"160000,{'1' * 40},vendor/pinned")
    git(repo, "commit", "-q", "-m", "pin a gitlink")
    git(repo, "mv", "docs/b.md", "docs/d.md")
    rename = commit("rename a record", {})
    git(repo, "merge", "-q", "--no-ff", "--no-commit", "side")
    merge = commit(f"merge {F1}!42", {"docs/merge.md": "use .aigw-ci-cache/123456789 here\n"})
    git(repo, "tag", "-a", "v1", "-m", f"release via {H1}:2222")
    tag = git(repo, "rev-parse", "v1")
    return repo, {root: "root", side: "side", rename: "rename", merge: "merge", tag: "tag"}


def _results(repo: Path, witness: Witness) -> list[bytes]:
    """Re-read the witnessed message or blob independently and list its attributed images."""
    if witness.path:
        text = git(repo, "show", f"{witness.object}:{witness.path}")
    else:
        text = git(repo, "cat-file", "-p", witness.object).partition("\n\n")[2]
    spans = (span for line in text.splitlines() for span in replacement_spans(line, FEED))
    return [attributed(span)[1] for span in spans if span.form != "manual"]


def test_counts_and_witnesses_agree_over_a_whole_history(tmp_path: Path) -> None:
    """Merges, roots, renames, shared blobs and tag-only items count once; witnesses resolve.

    Each item counts once in the first object that holds it, and every witness names a result of
    its own entry in a message or blob that a reader can re-read.
    """
    repo, labels = _history(tmp_path)

    found = occurrences(original_sightings(repo, ("v1",)), FEED)

    observed: dict[str, list[tuple[str, str, int]]] = {}
    for item in found:
        place = (labels[item.witness.object], item.witness.path, item.witness.n)
        observed.setdefault(ENTRIES[item.image], []).append(place)
    assert observed == VERSION_1
    assert {ENTRIES[image]: count for image, count in counts(found).items()} == {
        label: len(places) for label, places in VERSION_1.items()
    }
    for item in found:
        assert _results(repo, item.witness).count(item.image) >= item.witness.n


def test_the_walk_keeps_links_headers_and_names_and_what_reaches_an_item(tmp_path: Path) -> None:
    """Commits link their tree and parents, a tag its target; a gitlink is named but not linked.

    An item reaches every descendant of the commit that first holds it, and the tag over them.
    """
    repo, labels = _history(tmp_path)
    by_label = {label: oid for oid, label in labels.items()}

    history = original_history(repo, ("v1",))

    merge = git(repo, "rev-parse", f"{by_label['merge']}^@").split()
    assert history.links[by_label["merge"]] == (git(repo, "rev-parse", "v1^{tree}"), *merge)
    assert history.links[by_label["tag"]] == (by_label["merge"],)
    assert history.commits[0] == by_label["root"]
    assert history.commits[-1] == by_label["merge"]
    assert "tagger " in history.headers[by_label["tag"]]
    pinned = git(repo, "rev-parse", f"{by_label['rename']}~1:vendor")
    assert history.names[pinned] == ("pinned",)
    assert history.links[pinned] == ()
    side = git(repo, "rev-parse", f"{by_label['side']}:docs/s.md")
    assert reaching(history, {side}) == {by_label["side"], by_label["merge"], by_label["tag"]}


def test_a_revision_that_peels_to_no_commit_refuses(tmp_path: Path) -> None:
    """A tag of a blob has no commit and path to name in a witness, so the walk refuses it."""
    repo = tmp_path / "repo"
    git(tmp_path, "init", "-q", str(repo))
    (repo / "a.md").write_text("a\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "root")
    git(repo, "tag", "-a", "blob-tag", "-m", "a blob", git(repo, "rev-parse", "HEAD:a.md"))
    with pytest.raises(ValueError, match="rebuild_original_unplaced"):
        original_sightings(repo, ("HEAD", "blob-tag"))


def test_a_tag_message_ends_before_its_last_signature_armor() -> None:
    """As in Git, the last line that opens a known armor starts the signature, in any format."""
    body = b"release notes\n-----BEGIN PGP SIGNATURE----- is quoted here\n"
    head = b"object 0\ntype commit\ntag v1\ntagger T <t@example.invalid> 0 +0000\n\n"
    for armor in (b"SSH SIGNATURE", b"PGP SIGNATURE", b"SIGNED MESSAGE"):
        signed = (
            head + body + b"-----BEGIN " + armor + b"-----\nAAAA\n-----END " + armor + b"-----\n"
        )
        assert tag_message(signed) == body
    assert tag_message(head + b"unsigned\n") == b"unsigned\n"


def test_git_finds_a_messages_trailers_and_its_closing_paragraph(tmp_path: Path) -> None:
    """Declared ones are one result each, and what they hold is not scanned again."""
    repo = tmp_path / "repo"
    git(tmp_path, "init", "-q", "-b", "main", str(repo))
    (repo / "a.md").write_text("plain\n", encoding="utf-8")
    git(repo, "add", "-A")
    closing, trailer = f"Generated with a tool by {H1}", f"Co-Authored-By: Bot <bot@{H1}>"
    git(repo, "commit", "-q", "-m", f"subject\n\nbody names {H1}\n\n{closing}\n\n{trailer}")

    message, _blob = original_sightings(repo, ("HEAD",))
    found = occurrences([message], Feed.of(hosts=[H1], trailers=[trailer], paragraphs=[closing]))

    assert (message.trailers, message.closing) == ((trailer,), closing)
    assert [(item.kind, item.image) for item in found] == [
        ("trailer", rebuild_image("trailer", trailer)),
        ("paragraph", rebuild_image("paragraph", closing)),
        ("host", marker_image("host", H1)),
    ]
