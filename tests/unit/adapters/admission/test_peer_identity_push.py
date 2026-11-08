"""A push refuses a protected peer's identity that it adds beyond the peer's advertisement."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.admission.peer_identity_push import mode_at
from ethos.adapters.admission.peer_identity_push import peer_identity_push_gaps
from ethos.application.peer_identity import peer_identity_backstop
from ethos.application.peer_identity import peer_identity_status
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_publication_topology

if TYPE_CHECKING:
    from pathlib import Path

# A reserved name the owner opts in as private, so the fixture names no private-class literal.
H1 = "forge.example.invalid"
# The one literal the pushed commit adds: a bare host in the first line of its only file.
NAMED = "peer_identity_literal:host:1:1:1"


def _profile(repo: Path, mode: str) -> str:
    (repo / ".ethos").mkdir(exist_ok=True)
    text = f'profile_id = "push-check"\n\n[peer_identity]\nmode = "{mode}"\n'
    (repo / ".ethos/profile.toml").write_text(text, encoding="utf-8")
    return commit_fixture(repo, f"declare the {mode} peer identity mode")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Provide a repository whose protected peer is a local bare remote holding the base."""
    repo = init_git_repo(tmp_path / "repo")
    write_publication_topology(repo)
    peer = tmp_path / "peer.git"
    git(tmp_path, "init", "--bare", "-q", str(peer))
    git(repo, "remote", "add", "gitlab", str(peer))
    git(repo, "config", "remote.gitlab.forgePrivate", "true")
    git(repo, "config", "--add", "remote.gitlab.forgeFormer", f"host={H1}")
    _profile(repo, "required")
    git(repo, "push", "-q", "--no-verify", "gitlab", "HEAD:refs/heads/dev")
    return repo


def _gaps(repo: Path, trusted: str, advertisement: str = "network") -> tuple[list[str], list[str]]:
    head = git(repo, "rev-parse", "HEAD")
    return peer_identity_push_gaps(
        repo, remote="gitlab", pushed=head, trusted=trusted, advertisement=advertisement
    )


def test_a_push_refuses_the_identity_it_adds_and_only_that(repo: Path) -> None:
    """A fed host that a push adds refuses by its position; advertised history is never read."""
    base = git(repo, "rev-parse", "HEAD")
    (repo / "notes.md").write_text(f"plain\nssh git@{H1} now\n", encoding="utf-8")
    commit_fixture(repo, f"name {H1} in the message")

    assert _gaps(repo, base) == (
        ["peer_identity_literal:host:1:0:1", "peer_identity_literal:host:1:1:2"],
        [],
    )
    git(repo, "push", "-q", "--no-verify", "gitlab", "HEAD:refs/heads/dev")
    assert _gaps(repo, base) == ([], [])


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("disabled", ([], [])),
        ("invalid", ([], ["peer_identity_mode_unread"])),
        ("unfed", ([], [])),
        ("deleted", ([], [])),
    ],
)
def test_the_mode_decides_whether_a_push_is_read(
    repo: Path, case: str, expected: tuple[list[str], list[str]]
) -> None:
    """A disabled mode, an unread one, an unfed peer or a deletion reads nothing."""
    (repo / "notes.md").write_text(f"ssh git@{H1}\n", encoding="utf-8")
    pushed = commit_fixture(repo, "name a peer")
    trusted = git(repo, "rev-parse", "HEAD~1")
    if case == "disabled":
        pushed = trusted = _profile(repo, "disabled")
    elif case == "invalid":
        (repo / ".ethos/profile.toml").write_text("profile_id = 1\n", encoding="utf-8")
        pushed = trusted = commit_fixture(repo, "break the profile")
    elif case == "unfed":
        git(repo, "config", "--unset", "remote.gitlab.forgePrivate")
    elif case == "deleted":
        pushed = "0" * 40
    found = peer_identity_push_gaps(
        repo, remote="gitlab", pushed=pushed, trusted=trusted, advertisement="network"
    )
    assert found == expected


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("unreachable", ["peer_identity_range_unknown:gitlab"]),
        ("tracking", [NAMED]),
        ("untracked", [NAMED]),
        ("tag", ["peer_identity_literal:host:0:0:1", NAMED]),
    ],
)
def test_the_advertisement_bounds_what_a_push_adds(
    repo: Path, case: str, expected: list[str]
) -> None:
    """A tracking view, a peer without tips and a tag message read as the network does."""
    (repo / "notes.md").write_text(f"ssh git@{H1}\n", encoding="utf-8")
    pushed = commit_fixture(repo, "name a peer")
    trusted = git(repo, "rev-parse", "HEAD~1")
    advertisement = "tracking" if case in {"tracking", "untracked"} else "network"
    if case == "unreachable":
        git(repo, "remote", "set-url", "gitlab", str(repo.parent / "absent.git"))
    elif case == "untracked":
        for ref in git(repo, "for-each-ref", "--format=%(refname)", "refs/remotes/").split():
            git(repo, "update-ref", "-d", ref)
    elif case == "tag":
        git(repo, "tag", "-a", "v1", "-m", f"release for {H1}")
        pushed = git(repo, "rev-parse", "v1")
    found = peer_identity_push_gaps(
        repo, remote="gitlab", pushed=pushed, trusted=trusted, advertisement=advertisement
    )
    assert found == (expected, [])


@pytest.mark.parametrize(
    ("revision", "mode"),
    [
        ("", None),
        ("0" * 40, None),
        ("no-such-revision", None),
        ("EMPTY", "disabled"),
        ("HEAD", "required"),
    ],
)
def test_the_mode_is_read_at_one_commit(repo: Path, revision: str, mode: str | None) -> None:
    """No revision or an unknown one is unread; a commit without a profile is `disabled`."""
    if revision == "EMPTY":
        revision = git(
            repo, "commit-tree", "4b825dc642cb6eb9a060e54bf8d69288fbee4904", "-m", "empty"
        )
    assert mode_at(repo, revision) == mode


@pytest.mark.parametrize("case", ["inert", "baseline", "required", "disabled"])
def test_the_ci_backstop_refuses_only_a_fed_literal_under_required(repo: Path, case: str) -> None:
    """Without the job's variables it is inert; without a base it advises; it refuses by mode."""
    base = git(repo, "rev-parse", "HEAD")
    if case == "disabled":
        base = _profile(repo, "disabled")
    (repo / "notes.md").write_text(f"ssh git@{H1}\n", encoding="utf-8")
    head = commit_fixture(repo, "name a peer")
    environ = {} if case == "inert" else {"CI_SERVER_HOST": H1, "CI_PROJECT_PATH": "team/tools"}
    remote_head = base
    if case == "baseline":
        # A new branch's zero base falls back to the tracking ref, which this clone lacks.
        remote_head = "0" * 40
        for ref in git(repo, "for-each-ref", "--format=%(refname)", "refs/remotes/").split():
            git(repo, "update-ref", "-d", ref)

    report = peer_identity_backstop(
        repo, proposed=head, remote_head=remote_head, remote="gitlab", environ=environ
    )

    expected = {
        "inert": ("pass", "inert", []),
        "baseline": ("pass", "baseline_missing", []),
        "required": ("block", "refused", ["peer_identity_literal:host:1:1:1"]),
        "disabled": ("pass", "disabled", []),
    }[case]
    assert (report["verdict"], report["state"], report["required_gaps"]) == expected


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("disabled", ["peer_identity_protected_peer_disabled"]),
        ("required", []),
        ("unfed", []),
        ("invalid", ["peer_identity_mode_unread"]),
    ],
)
def test_status_names_a_protected_peer_left_unchecked(
    repo: Path, mode: str, expected: list[str]
) -> None:
    """A protected peer under `disabled`, or an unread mode, is advised; others are quiet."""
    if mode in {"disabled", "invalid"}:
        _profile(repo, "disabled")
    if mode == "invalid":
        (repo / ".ethos/profile.toml").write_text("profile_id = 1\n", encoding="utf-8")
        commit_fixture(repo, "break the profile")
    elif mode == "unfed":
        git(repo, "config", "--unset", "remote.gitlab.forgePrivate")
    assert peer_identity_status(repo) == expected


def test_status_carries_the_advisory_in_its_summary_and_never_as_a_gap(repo: Path) -> None:
    """`ethos status --json` names a protected peer under `disabled` in its summary only."""
    _profile(repo, "disabled")
    completed = run_ethos_raw("status", "--root", str(repo), "--json", cwd=repo)
    result = json.loads(completed.stdout)
    assert result["summary"]["peer_identity_advisories"] == [
        "peer_identity_protected_peer_disabled"
    ]
    assert not [gap for gap in result["required_gaps"] if gap.startswith("peer_identity")]
