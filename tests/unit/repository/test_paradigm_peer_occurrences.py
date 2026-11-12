"""Each scan result is one occurrence of one entry, keyed by that entry kind's own pre-image."""

from __future__ import annotations

import hashlib
import hmac

import pytest

from ethos.repository.paradigm.peer_identity import Feed
from ethos.repository.paradigm.peer_identity import Sighting
from ethos.repository.paradigm.peer_identity import Witness
from ethos.repository.paradigm.peer_identity import attributed
from ethos.repository.paradigm.peer_identity import counts
from ethos.repository.paradigm.peer_identity import entry_digest
from ethos.repository.paradigm.peer_identity import marker
from ethos.repository.paradigm.peer_identity import marker_image
from ethos.repository.paradigm.peer_identity import occurrences
from ethos.repository.paradigm.peer_identity import read_key
from ethos.repository.paradigm.peer_identity import rebuild_image
from ethos.repository.paradigm.peer_identity import replacement_spans

KEY = read_key("ab" * 32)
H1 = "forge.example.invalid"
F1 = "team/infra/tools"
FEED = Feed.of(hosts=[H1], ports=[8443, 2222], paths=[F1], ids=[123456789], citations=[f"{F1}!42"])


def test_each_entry_kind_keys_its_own_domain_separated_pre_image() -> None:
    """Spans, hosts and paths key F's marker images; the rebuild's kinds key their own.

    Ports, IDs, trailers, paragraphs and originals' names are domain-separated, and no two kinds
    share a digest.
    """
    images = {
        "span": marker_image("prefix", H1, "8443", F1),
        "host": marker_image("host", H1),
        "path": marker_image("path", path=F1),
        "port": rebuild_image("port", "8443"),
        "id": rebuild_image("id", "id.api-projects", "123456789"),
        "trailer": rebuild_image("trailer", "Co-authored-by: A <a@example.invalid>"),
        "paragraph": rebuild_image("paragraph", b"Generated with \xff\n"),
        "oid": rebuild_image("oid", "0" * 40),
    }
    assert images["span"] == b"ethos.private-peer.v1\0prefix\0" + f"{H1}\x008443\0{F1}".encode()
    assert images["port"] == b"ethos.rebuild.v1\0port\x008443"
    assert images["id"] == b"ethos.rebuild.v1\0id\0id.api-projects\x00123456789"
    assert images["trailer"] == (
        b"ethos.rebuild.v1\0trailer\0Co-authored-by: A <a@example.invalid>"
    )
    assert images["paragraph"] == b"ethos.rebuild.v1\0paragraph\0Generated with \xff\n"
    assert images["oid"] == b"ethos.rebuild.v1\0oid\0" + b"0" * 40
    digests = {kind: entry_digest(KEY, image) for kind, image in images.items()}
    for kind, digest in digests.items():
        assert digest == hmac.new(KEY, images[kind], hashlib.sha256).hexdigest()
    assert len(set(digests.values())) == len(digests)
    assert "".join(marker(KEY, "prefix", H1, "8443", F1).split(".")[:2]) == digests["span"]


@pytest.mark.parametrize(
    ("line", "kinds"),
    [
        (f"https://{H1}:8443/{F1}.git", ["span"]),
        (f"git@{H1}:{F1}", ["host", "path"]),
        (f"ssh {H1} and {H1}:2222", ["host", "span"]),
        (f"cite {F1}!42 or {F1}!7", ["span", "path"]),
        ("api team%2Finfra%2Ftools", ["path"]),
        ("projects/123456789 on port 8443", ["id", "port"]),
    ],
)
def test_each_result_is_attributed_to_exactly_one_entry_kind(line: str, kinds: list[str]) -> None:
    """A span wins over its own host, port and path; a citation is a span; parts stand alone."""
    assert [attributed(span)[0] for span in replacement_spans(line, FEED)] == kinds


def test_each_object_is_read_once_and_each_entry_numbered_within_it() -> None:
    """A blob met again adds nothing, and a tag witnesses its own message.

    The second path of a blob and its later commit read nothing; a `manual` result is no entry's.
    """
    blob = f"ssh {H1}\nssh {H1} on port 8443\nsee https://{H1}/unknown/path\n"
    sightings = [
        Sighting("c1", "c1", "", "project 123456789\n"),
        Sighting("b1", "c1", "a.md", blob),
        Sighting("b1", "c1", "b.md", blob),
        Sighting("b1", "c2", "a.md", blob),
        Sighting("t1", "t1", "", f"tag {H1}:2222\n"),
    ]

    found = occurrences(sightings, FEED)

    assert [(occurrence.kind, occurrence.witness) for occurrence in found] == [
        ("id", Witness("c1", "", 1)),
        ("host", Witness("c1", "a.md", 1)),
        ("host", Witness("c1", "a.md", 2)),
        ("port", Witness("c1", "a.md", 1)),
        ("span", Witness("t1", "", 1)),
    ]
    assert counts(found) == {
        rebuild_image("id", "id.project-word", "123456789"): 1,
        marker_image("host", H1): 2,
        rebuild_image("port", "8443"): 1,
        marker_image("host", H1, "2222"): 1,
    }
