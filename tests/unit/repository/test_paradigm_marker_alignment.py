"""A keyless reader pairs a marker line with the removed line it reproduces."""

from __future__ import annotations

import hashlib

import pytest

from ethos.repository.paradigm.peer_identity import VERSION
from ethos.repository.paradigm.peer_identity import Feed
from ethos.repository.paradigm.peer_identity import alignment
from ethos.repository.paradigm.peer_identity import malformed_markers
from ethos.repository.paradigm.peer_identity import marker
from ethos.repository.paradigm.peer_identity import numbering
from ethos.repository.paradigm.peer_identity import read_key
from ethos.repository.paradigm.peer_identity import redact_text
from ethos.repository.paradigm.peer_identity import unkeyed

KEY = read_key("ab" * 32)
H1 = "forge.example.invalid"
F1 = "team/infra/tools"
FEED = Feed.of(hosts=[H1], ports=[8443, 2222], paths=[F1], ids=[123456789])
LINES = [
    f"clone https://user@{H1}:8443/{F1}.git into place",
    f"origin git@{H1}:{F1}.git",
    f"see {H1} and project 123456789 on port 2222",
    f"cache under projects/123456789/jobs and {F1}",
]


@pytest.mark.parametrize("original", LINES)
def test_every_redacted_line_pairs_with_its_original(original: str) -> None:
    """What the verb writes, the keyless reader pairs, span for span."""
    redacted = redact_text(original, FEED, KEY, numbering(KEY, FEED, original))
    spans = alignment(original, redacted)
    assert spans is not None
    assert all(H1 in span or F1 in span for span in spans)


@pytest.mark.parametrize(
    ("removed", "added"),
    [
        (f"clone https://{H1}/{F1}", f"fetch https://{marker(KEY, 'prefix', H1, '', F1)}"),
        (f"see {H1} now", f"see {marker(KEY, 'host', H1)} later"),
        ("see a host name here", f"see {marker(KEY, 'host', H1)} here"),
        ("project 123456789 x", f"project 12 x {marker(KEY, 'host', H1)}"),
        ("no marker here", "no marker here"),
    ],
)
def test_a_line_that_is_not_a_reproduction_does_not_pair(removed: str, added: str) -> None:
    """Changed literals, a span with spaces, an out-of-range number or no marker do not pair."""
    assert alignment(removed, added) is None


def test_a_marker_without_a_key_is_unkeyed_and_a_broken_one_is_malformed() -> None:
    """A plain digest of the pre-image is unkeyed; a token that ends like a marker is malformed."""
    fields = (VERSION, "host", H1, "", "")
    image = "\0".join(fields).encode()
    digest = hashlib.sha256(image).hexdigest()
    plain = f"{digest[:32]}.{digest[32:]}.private-peer.invalid"
    assert unkeyed(plain, H1)
    assert not unkeyed(marker(KEY, "host", H1), H1)
    assert malformed_markers(f"x {digest[:31]}.{digest[32:]}.private-peer.invalid y") == 1
    assert malformed_markers(f"x {plain} y") == 0


@pytest.mark.parametrize(
    ("line", "count"),
    [
        ("the marker `<hex32>.<hex32>.private-peer.invalid` names its form", 0),
        ("`<32 lowercase hex>.<32 lowercase hex>.private-peer.invalid`", 0),
        ("every marker ends in .private-peer.invalid, a reserved name", 0),
        (marker(KEY, "host", H1)[:65].upper() + ".private-peer.invalid", 1),
        ("0" + marker(KEY, "host", H1), 1),
    ],
)
def test_only_a_run_of_hexadecimal_labels_can_be_a_malformed_marker(line: str, count: int) -> None:
    """A placeholder or a bare suffix describes a marker; an uppercase or long label breaks one."""
    assert malformed_markers(line) == count
