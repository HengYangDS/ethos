"""Version 1 of the rebuild record parses whole, or refuses by a fixed gap that repeats no value."""

from __future__ import annotations

import pytest

from ethos.contracts.outcome import OutcomeError
from ethos.repository.rebuild_record import Keyed
from ethos.repository.rebuild_record import parse_record

D, E = "a" * 64, "b" * 64
OID = "c" * 40
RECORD = f"""
version = 1
id = "aigw-2026-11"
owner = "97f828"
reason = "remove a private peer's identity from published history"
expires = 2026-12-31T00:00:00Z
base = {{ digest = "{D}" }}
key = {{ generation = "0123456789abcdef" }}

[refs."refs/heads/dev"]
disposition = "rebuild"
old = "old"
peers = {{ gitlab = "old", github = "old" }}

[refs."refs/tags/v0.1.0"]
disposition = "retag"
old = "{OID}"
peers = {{ gitlab = {{ digest = "{E}" }}, github = "absent" }}

[transform]
retain = ["api/v4/projects"]

[[transform.trailers]]
digest = "{D}"
count = 3
witness = {{ object = "{OID}", n = 1 }}

[[transform.hosts]]
digest = "{E}"
count = 2
witness = {{ object = {{ digest = "{D}" }}, path = "a.md", n = 2 }}

[[transform.ids]]
contexts = ["id.api-projects", "id.ci-project-id"]
digests = ["{D}", "{E}"]
count = 4
witness = {{ object = "{OID}", n = 1 }}
"""


def test_a_complete_record_parses_with_its_names_and_entries() -> None:
    """Clear and keyed names, peer states, typed entries and public prefixes all read back."""
    record = parse_record(RECORD)

    tag = record.refs["refs/tags/v0.1.0"]
    assert (record.version, record.id, record.key.generation) == (
        1,
        "aigw-2026-11",
        "0123456789abcdef",
    )
    assert (tag.disposition, tag.old, tag.peers["github"]) == ("retag", OID, "absent")
    assert tag.peers["gitlab"] == Keyed(digest=E)
    assert record.transform.hosts[0].witness.object == Keyed(digest=D)
    assert record.transform.ids[0].contexts == ("id.api-projects", "id.ci-project-id")
    assert record.transform.retain == ("api/v4/projects",)


@pytest.mark.parametrize(
    ("before", "after", "gaps"),
    [
        (
            f'[[transform.hosts]]\ndigest = "{E}"',
            '[[transform.hosts]]\ndigest = "forge.example.invalid"',
            ["rebuild_record_free_string"],
        ),
        (
            "[transform]\n",
            '[transform]\nhost = "forge.example.invalid"\n',
            ["rebuild_record_free_string"],
        ),
        ('"id.ci-project-id"]', '"id.no-such-context"]', ["rebuild_id_context_unknown:0"]),
        ('"id.ci-project-id"]', '"id.api-projects"]', ["rebuild_id_context_repeated:0"]),
        ('"id.ci-project-id"]', '"port.word"]', ["rebuild_id_context_unknown:0"]),
        (
            f'contexts = ["id.api-projects", "id.ci-project-id"]\ndigests = ["{D}", "{E}"]',
            "contexts = []\ndigests = []",
            ["rebuild_id_context_missing:0"],
        ),
        (
            f'digests = ["{D}", "{E}"]',
            f'digests = ["{D}"]',
            ["rebuild_record_invalid:transform.ids.0"],
        ),
        ("version = 1", "version = 2", ["rebuild_record_invalid:version"]),
        ('disposition = "rebuild"', 'disposition = "rename"', ["rebuild_record_invalid:refs"]),
        (
            'key = { generation = "0123456789abcdef" }',
            'key = { service = "x" }',
            ["rebuild_record_invalid:key"],
        ),
        ("count = 3", "count = 0", ["rebuild_record_invalid:transform"]),
        ("version = 1", "version = 1\nversion = 1", ["rebuild_record_unreadable"]),
    ],
)
def test_a_record_that_cannot_bind_refuses_by_a_fixed_gap(
    before: str, after: str, gaps: list[str]
) -> None:
    """A free string, an unknown or repeated context, or an invalid field names its gap."""
    assert before in RECORD
    with pytest.raises(OutcomeError) as refused:
        parse_record(RECORD.replace(before, after, 1))

    assert list(refused.value.outcome.gaps) == gaps
