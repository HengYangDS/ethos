"""Readiness's quote counter and in-memory transform, over synthetic originals."""

from __future__ import annotations

from ethos.adapters.repo.commit.rebuild.discovery import quoted_ids
from ethos.adapters.repo.commit.rebuild.discovery import transformed
from ethos.adapters.repo.commit.rebuild.originals import History
from ethos.repository.paradigm.peer_identity import Feed
from ethos.repository.paradigm.peer_identity import Sighting
from ethos.repository.paradigm.peer_identity import marker
from tests.support.rebuild import H1
from tests.support.rebuild import KEY
from tests.support.rebuild import RECORD

ONE, TWO, TAG = "abcdef1" + "0" * 33, "abcdef1" + "9" * 33, "1234567" + "8" * 33


def test_quotes_count_by_where_they_stand_and_what_they_quote_and_a_shared_prefix_refuses() -> None:
    """A token that prefixes one rewritten object counts; two make it ambiguous; digests stay."""
    texts = (
        ("c1", "", f"revert {TWO[:12]} and {TAG[:9]}, not {ONE[:6]} or {'f' * 64}"),
        ("t1", "", f"tags {TWO}"),
        ("b1", "notes.md", f"see {ONE[:7]} and {TWO[:10]}\n"),
        ("b2", RECORD, f'base = "{TWO}"\n'),
    )
    history = History(
        [Sighting(oid, "c1", path, text) for oid, path, text in texts], ["c1"], {}, {}, {}
    )

    found, ambiguous = quoted_ids(history, {ONE: "commit", TWO: "commit", TAG: "tag"}, RECORD)

    assert found == {"blob": {"commit": 1}, "commit": {"commit": 1, "tag": 1}, "tag": {"commit": 1}}
    assert ambiguous == 1


def test_the_transform_keeps_a_retained_prefix_and_drops_declared_message_items() -> None:
    """The host before a retained prefix is replaced; the prefix's bytes and the rest stay."""
    trailer, closing = f"Co-Authored-By: Bot <bot@{H1}>", "Generated with a tool"
    text = f"jobs https://{H1}/api/v4/projects/7/jobs\n\n{closing}\n\n{trailer}\n"
    feed = Feed.of(hosts=[H1], retain=["api/v4/projects"], trailers=[trailer], paragraphs=[closing])

    rebuilt = transformed(Sighting("c1", "c1", "", text, (trailer,), closing), feed, KEY)

    assert rebuilt == f"jobs https://{marker(KEY, 'host', H1)}/api/v4/projects/7/jobs\n\n\n\n"
    assert transformed(Sighting("c2", "c2", "", f"ssh git@{H1}:x/y\n"), feed, KEY) is None
