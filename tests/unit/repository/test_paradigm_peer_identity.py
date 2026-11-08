"""One grammar names private peer identity: its forms, keyed markers and numbers."""

from __future__ import annotations

import hashlib

import pytest

from ethos.repository.paradigm.peer_identity import MARKER
from ethos.repository.paradigm.peer_identity import Feed
from ethos.repository.paradigm.peer_identity import follow_digests
from ethos.repository.paradigm.peer_identity import generation
from ethos.repository.paradigm.peer_identity import marker
from ethos.repository.paradigm.peer_identity import number
from ethos.repository.paradigm.peer_identity import numbering
from ethos.repository.paradigm.peer_identity import read_key
from ethos.repository.paradigm.peer_identity import redact_line
from ethos.repository.paradigm.peer_identity import redact_text
from ethos.repository.paradigm.peer_identity import replacement_spans

KEY = read_key("ab" * 32 + "\n")
H1 = "forge.example.invalid"
F1 = "team/infra/tools"
FEED = Feed.of(hosts=[H1], ports=[8443, 2222], paths=[F1, "old/team", "team"], ids=[123456789])


def _forms(line: str) -> list[tuple[str, str]]:
    return [(span.form, line[span.start : span.end]) for span in replacement_spans(line, FEED)]


@pytest.mark.parametrize(
    ("line", "forms"),
    [
        (f"https://user@{H1}:8443/{F1}.git", [("url", f"{H1}:8443/{F1}.git")]),
        (f"ssh://git@{H1}:2222/{F1}/x", [("url", f"{H1}:2222/{F1}")]),
        (f"git@{H1}:{F1}.git", [("scp", H1), ("path", f"{F1}.git")]),
        (f"{H1}:8443/{F1}", [("authority", f"{H1}:8443/{F1}")]),
        (f"ssh git@{H1} now", [("host", H1)]),
        (f"see {H1}: next", [("manual", f"{H1}:")]),
        (f"https://{H1}/unknown/path", [("manual", H1)]),
        ("moved from old/team last year", [("path", "old/team")]),
        ("team alone is not a path", []),
        ("projects/123456789/jobs and port 8443", [("id", "123456789"), ("port", "8443")]),
        ("port 22 and projects/1234567890", []),
        (f"sub.{H1}x is another host", []),
    ],
)
def test_each_occurrence_takes_one_form(line: str, forms: list[tuple[str, str]]) -> None:
    """Neighbours and the declared ports decide the form; unclassified occurrences are manual."""
    assert _forms(line) == forms


@pytest.mark.parametrize("before", ["", "//", "//user@", "ssh git@", "x "])
@pytest.mark.parametrize("after", ["", " end", ":8443", f":8443/{F1}", f":{F1}", f"/{F1}", ":"])
def test_each_neighbourhood_yields_exactly_one_host_form(before: str, after: str) -> None:
    """The forms are disjoint: every host neighbourhood yields one form."""
    line = f"{before}{H1}{after}"
    forms = [span.form for span in replacement_spans(line, FEED) if span.start <= len(before)]
    url = "//" in before
    if after == ":" and not url:
        expected = "manual"
    elif after.startswith(":t") and not url:
        expected = "scp"
    else:
        expected = "url" if url else "authority" if after.startswith(":8443") else "host"
    assert forms == [expected], line


def test_markers_are_keyed_canonical_and_distinct_per_shape() -> None:
    """Case, edge slashes and `.git` do not change a marker; the kind and the key do."""
    url = marker(KEY, "prefix", H1, "8443", F1)
    assert MARKER.fullmatch(url)
    assert url == marker(KEY, "prefix", H1.upper(), "8443", "/Team/Infra/Tools.git")
    assert url != marker(KEY, "host", H1)
    assert marker(KEY, "host", H1) != marker(read_key("cd" * 32), "host", H1)
    assert generation(KEY) != generation(read_key("cd" * 32))
    assert len(generation(KEY)) == 16


@pytest.mark.parametrize("text", ["ab" * 31, "AB" * 32, "0" * 64, "ab" * 32 + "\n\n"])
def test_a_key_that_cannot_key_refuses(text: str) -> None:
    """A short, upper-case, all-zero or twice-terminated key refuses."""
    with pytest.raises(ValueError, match="redaction_key_invalid"):
        read_key(text)


def test_numbers_avoid_the_original_the_fed_values_and_the_domain() -> None:
    """A replacement lies in its range, avoids every fed value and is absent from the domain."""
    first = number(KEY, "id", 123456789, taken={123456789}, domain="")
    assert 100_000_000 <= first <= 999_999_999
    assert first != 123456789
    assert number(KEY, "id", 123456789, taken={123456789}, domain=f"x {first} y") != first
    with pytest.raises(ValueError, match="numeric_replacement_exhausted"):
        number(KEY, "port", 8443, taken=set(range(1024, 65536)), domain="")


def test_a_line_keeps_scheme_userinfo_and_its_other_bytes() -> None:
    """Only the spans change; a manual occurrence refuses the line."""
    line = f"clone https://user@{H1}:8443/{F1}.git into port 8443 here"
    replaced = redact_line(line, replacement_spans(line, FEED), KEY, {("port", 8443): 30001})
    assert replaced.startswith("clone https://user@")
    assert replaced.endswith(" into port 30001 here")
    assert H1 not in replaced
    assert "team/infra" not in replaced
    manual = f"see {H1}: next"
    with pytest.raises(ValueError, match="peer_occurrence_unclassified"):
        redact_line(manual, replacement_spans(manual, FEED), KEY, {})


def test_a_text_redacts_line_by_line_and_rederives_exactly() -> None:
    """The same key and base give the same text; another key gives another."""
    base = f"origin git@{H1}:{F1}.git\nproject 123456789 on port 8443\nplain line\n"
    numbers = numbering(KEY, FEED, base)
    head = redact_text(base, FEED, KEY, numbers)
    assert head.endswith("plain line\n")
    assert H1 not in head
    assert "123456789" not in head
    assert redact_text(base, FEED, KEY, numbering(KEY, FEED, base)) == head
    assert head != redact_text(base, FEED, read_key("cd" * 32), numbers)


def test_a_record_follows_the_digest_of_a_redacted_file() -> None:
    """A digest a record holds is rewritten only where a redaction changed that file."""
    old, new = hashlib.sha256(b"a").hexdigest(), hashlib.sha256(b"b").hexdigest()
    other = hashlib.sha256(b"c").hexdigest()
    text = f'{{"sha256": "{old}", "other": "{other}"}}'
    assert follow_digests(text, {old: new}) == f'{{"sha256": "{new}", "other": "{other}"}}'
