"""Materialize signature-repair repositories and their failure boundaries."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import ethos.adapters.mutation.accepted.signature as repair
from ethos.adapters.repo.attestation_set import read_attestation_set
from tests.support.fixture_signer import configure_fixture_signer
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_paradigm_toolchain
from tests.support.governed_repository import write_release_mirror
from tests.support.subprocesses import kill_after_marker

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    import pytest


def untrusted_signer_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, signed: bool, key_type: str = "ed25519"
) -> tuple[Path, Path, str, str]:
    """Configure one local signer that the repository's empty trust anchor does not trust yet."""
    for role in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{role}_NAME", "Test User")
        monkeypatch.setenv(f"GIT_{role}_EMAIL", "owner@example.com")
    repo = init_git_repo(tmp_path / "repo")
    anchor = configure_fixture_signer(repo, own=tmp_path, trusted=False, key_type=key_type)
    git(repo, "config", "user.email", "owner@example.com")
    if signed:
        git(repo, "-c", "commit.gpgsign=true", "commit", "--allow-empty", "-m", "signed target")
    target = git(repo, "rev-parse", "HEAD")
    return repo, anchor, target, hashlib.sha256(anchor.read_bytes()).hexdigest()


def repair_fixture_history(
    root: Path,
    backup: Path,
    *,
    corrections: Mapping[str, object],
    refs: tuple[str, ...] = ("refs/heads/dev",),
) -> str:
    """Execute one positive native history repair with a verified original bundle of `refs`."""
    git(root, "bundle", "create", str(backup), *refs)
    result = repair.repair_signature(
        root=root,
        expect_head=git(root, "rev-parse", "HEAD"),
        corrections=corrections,
        reason="Repair selected test history",
        backup=backup,
        apply=True,
        authorized=True,
    )
    assert result["verdict"] == "pass", result
    head = result["head"]
    assert isinstance(head, str)
    return head


def signature_repository(
    tmp_path: Path, *, coupled: bool = False, legacy_mirror: bool = False
) -> tuple[Path, str, Path]:
    """Commit an unsigned accepted head; `legacy_mirror` couples main the pre-2026-10-16 way."""
    repo = init_git_repo(tmp_path / "repo")
    (repo / ".ethos").mkdir()
    (repo / ".ethos/profile.toml").write_text('profile_id = "signature-fixture"\n')
    if legacy_mirror:
        (repo / ".ethos/workspace.toml").write_text(
            '[branch_roles]\nrelease_mirror = "accepted_ff"\n'
        )
    else:
        write_release_mirror(repo, "accepted_ff" if coupled else "independent")
    write_paradigm_toolchain(repo)
    git(repo, "add", ".ethos", ".config/mise")
    git(repo, "-c", "commit.gpgsign=false", "commit", "-m", "fix: accept an unsigned head")
    old = git(repo, "rev-parse", "HEAD")
    git(repo, "branch", "candidate/dev", old)
    git(repo, "branch", "main", old)
    candidate = tmp_path / "candidate"
    git(repo, "worktree", "add", str(candidate), "candidate/dev")
    configure_fixture_signer(repo, own=tmp_path)
    return repo, old, candidate


def interrupted_signature(repo, old, monkeypatch):
    """Stop at the real effect boundary after durable signing evidence exists."""

    def interrupt(*_args, **_kwargs):
        error = "injected before ref CAS"
        raise OSError(error)

    with monkeypatch.context() as scope:
        scope.setattr(repair, "execute_git_effect", interrupt)
        observed = repair.repair_signature(root=repo, expect_head=old, apply=True, authorized=True)
    assert observed["verdict"] != "pass"
    _, records = read_attestation_set(repo)
    return records


def killed_signature_repair(
    repo: Path, old: str, first: str, backup: Path, *, boundary: str
) -> str:
    """Kill an owned repair child after a real effect, before its caller receives the ACK."""
    ready = repo.parent / "effect-ready"
    script = """
import sys
from pathlib import Path
from tests.support.subprocesses import pause_after_effect
import ethos.adapters.mutation.accepted.signature as repair
import ethos.adapters.repo.commit.history as history
import ethos.adapters.repo.git_effects as effects
repo, old, first, backup, marker, boundary = sys.argv[1:]
owner, name = {
    'signed-object': (history, 'create_signed_payload'),
    'ref-cas': (repair, 'execute_git_effect'),
    'ref-cas-unrecorded': (effects, '_run_effect_program'),
}[boundary]
pause_after_effect(owner, name, Path(marker))
repair.repair_signature(root=Path(repo), expect_head=old, corrections={first: {'resign': True}},
                      reason='Restore valid signatures', backup=Path(backup),
                      apply=True, authorized=True)
"""
    return kill_after_marker(
        repo, script, (str(repo), old, first, str(backup), str(ready), boundary), ready
    )
