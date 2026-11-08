"""A marker edit under a record root is admitted only when it reproduces the line it replaced."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.repo.commit.record_markers import record_marker_gaps
from ethos.repository.paradigm.peer_identity import VERSION
from ethos.repository.paradigm.peer_identity import Feed
from ethos.repository.paradigm.peer_identity import numbering
from ethos.repository.paradigm.peer_identity import read_key
from ethos.repository.paradigm.peer_identity import redact_text
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path

KEY = read_key("ab" * 32)
H1 = "forge.example.invalid"
FEED = Feed.of(hosts=[H1], ports=[8443], paths=["team/infra/tools"], ids=[123456789])
RECORD = "openspec/changes/archive/2026-01-01-old/design.md"
TEXT = f"origin https://{H1}:8443/team/infra/tools.git\nproject 123456789 here\nplain\n"
# The plain digest of the replaced span's pre-image: what an unkeyed redaction would write.
_FIELDS = (VERSION, "prefix", H1, "8443", "team/infra/tools")
_IMAGE = "\0".join(_FIELDS)
_digest = hashlib.sha256(_IMAGE.encode()).hexdigest()
PLAIN = f"{_digest[:32]}.{_digest[32:]}.private-peer.invalid"


def _commit(repo: Path, files: dict[str, str]) -> str:
    for relative, text in files.items():
        (repo / relative).parent.mkdir(parents=True, exist_ok=True)
        (repo / relative).write_text(text, encoding="utf-8")
    commit_fixture(repo, "record")
    return git(repo, "rev-parse", "HEAD")


@pytest.mark.parametrize(
    ("edit", "gap"),
    [
        ("redact", ""),
        ("added", "record_marker_unpaired"),
        ("reworded", "record_marker_unpaired"),
        ("unkeyed", "record_marker_unkeyed"),
        ("malformed", "record_marker_malformed"),
        ("outside", ""),
    ],
)
def test_a_marker_edit_pairs_with_what_it_replaced(tmp_path: Path, edit: str, gap: str) -> None:
    """A redaction pairs; a new marker file, changed words, an unkeyed or broken marker refuse."""
    repo = init_git_repo(tmp_path / "repo")
    _commit(repo, {RECORD: TEXT, "docs/notes.md": f"see {H1}\n"})
    redacted = redact_text(TEXT, FEED, KEY, numbering(KEY, FEED, TEXT))
    marker_line = redacted.splitlines()[0]
    files = {
        "redact": {RECORD: redacted},
        "added": {"openspec/changes/archive/2026-01-01-old/new.md": marker_line + "\n"},
        "reworded": {RECORD: redacted.replace("origin", "remote", 1)},
        "unkeyed": {
            RECORD: TEXT.replace(f"https://{H1}:8443/team/infra/tools.git", f"https://{PLAIN}", 1)
        },
        "malformed": {RECORD: TEXT + f"see x{PLAIN[2:]}0\n"},
        "outside": {"docs/notes.md": f"see {PLAIN} here\n"},
    }[edit]
    revision = _commit(repo, files)

    gaps = record_marker_gaps(repo, (revision,))

    assert [entry.split(":")[0] for entry in gaps] == ([gap] if gap else [])
