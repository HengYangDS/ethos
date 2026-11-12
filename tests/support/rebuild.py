"""A governed repository whose protected peer a rebuild record names, and that record.

The peer's host and namespace are reserved names, so no fixture holds a private-class literal.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.paradigm.peer_identity import entry_digest
from ethos.repository.paradigm.peer_identity import generation
from ethos.repository.paradigm.peer_identity import marker_image
from ethos.repository.paradigm.peer_identity import read_key
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_publication_topology

if TYPE_CHECKING:
    from pathlib import Path

KEY_TEXT = "ab" * 32 + "\n"
KEY = read_key(KEY_TEXT)
H1, F1 = "forge.example.invalid", "team/infra/tools"
RECORD = "openspec/changes/history-rebuild-map/rebuild.toml"
PEER = (
    f"clone https://{H1}/{F1}.git\nssh git@{H1} now\nsee {F1} here\nvisit example.com today\n"
    "mirror acme/tools and other/lone\n"
)
MAIN = """
[refs."refs/heads/main"]
disposition = "rebuild"
old = "old"
peers = { gitlab = "old", github = "absent" }
"""


def digest(image: bytes) -> str:
    """Key one pre-image as the record's entries do."""
    return entry_digest(KEY, image)


def peer_history(
    tmp_path: Path, *, signed: bool = True, extra: str = "", bare: bool = False
) -> tuple[Path, str]:
    """A repository whose protected peer the record's items name; returns it and its base.

    With `bare`, both peers are local bare repositories whose identity the local configuration
    keeps, so readiness lists them without a network.
    """
    repo = init_git_repo(tmp_path / "repo")
    write_publication_topology(repo)
    urls = {
        "gitlab": f"ssh://git@{H1}:2222/{F1}.git",
        "github": "https://github.com/acme/tools.git",
    }
    for name, url in urls.items():
        peer = tmp_path / f"{name}.git"
        if bare:
            git(tmp_path, "init", "--bare", "-q", str(peer))
        git(repo, "remote", "add", name, str(peer) if bare else url)
    git(repo, "config", "remote.gitlab.forgePrivate", "true")
    if bare:
        git(repo, "config", "remote.gitlab.forgeRepository", f"https://{H1}/{F1}")
        git(repo, "config", "remote.github.forgeRepository", "https://github.com/acme/tools")
    (repo / "docs").mkdir(exist_ok=True)
    (repo / "docs/peer.md").write_text(PEER + extra, encoding="utf-8")
    return repo, commit_fixture(repo, "docs: name a peer", signed=signed)


def entry(
    image: bytes, witness: str, count: int = 1, n: int = 1, path: str = "docs/peer.md"
) -> str:
    """One transform entry whose witness names a result in the blob at `path` or a message."""
    place = f', path = "{path}"' if path else ""
    return (
        f'{{ digest = "{digest(image)}", count = {count}, '
        f'witness = {{ object = "{witness}"{place}, n = {n} }} }}'
    )


def record(origin: str, **edits: str) -> str:
    """A complete record over `peer_history` from its base `origin`, with fields edited."""
    fields = {
        "generation": generation(KEY),
        "reason": "remove a private peer's identity from published history",
        "base": f'"{origin}"',
        "dev": '{ gitlab = "old", github = "old" }',
        "spans": entry(marker_image("prefix", H1, "", F1), origin),
        "hosts": entry(marker_image("host", H1), origin),
        "paths": entry(marker_image("path", path=F1), origin),
        "retain": "",
        "refs": "",
        "ids": "",
    } | edits
    return f"""version = 1
id = "fixture-rebuild"
owner = "97f828"
reason = "{fields["reason"]}"
expires = 2026-12-31T00:00:00Z
base = {fields["base"]}
key = {{ generation = "{fields["generation"]}" }}

[refs."refs/heads/dev"]
disposition = "rebuild"
old = "old"
peers = {fields["dev"]}
{fields["refs"]}
[transform]
spans = [{fields["spans"]}]
hosts = [{fields["hosts"]}]
paths = [{fields["paths"]}]
ids = [{fields["ids"]}]
retain = [{fields["retain"]}]
"""


def land_record(repo: Path, text: str, message: str = "docs: declare the rebuild") -> str:
    """Commit the record in its Change and return that accepted head."""
    (repo / RECORD).parent.mkdir(parents=True, exist_ok=True)
    (repo / RECORD).write_text(text, encoding="utf-8")
    return commit_fixture(repo, message)
