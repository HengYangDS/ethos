"""Configure native test signing and materialize signature-repair failure boundaries."""

from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING

import ethos.adapters.mutation.accepted.signature as repair
from ethos.adapters.repo.attestation_set import read_attestation_set
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import render_branch_policy

if TYPE_CHECKING:
    from pathlib import Path


def configure_signer(repo: Path, tmp_path: Path) -> None:
    """Create one owned native SSH signer and its explicit repository trust anchor."""
    executable = shutil.which("ssh-keygen")
    assert executable is not None
    key = tmp_path / "signer"
    subprocess.run(
        (executable, "-q", "-t", "ed25519", "-N", "", "-f", str(key)),
        check=True,
        capture_output=True,
        timeout=15,
    )
    trust = tmp_path / "trust"
    trust.mkdir(mode=0o700)
    anchor = trust / "allowed-signers"
    public = key.with_suffix(".pub").read_text()
    anchor.write_text(f'test@example.invalid namespaces="git" {public}')
    anchor.chmod(0o600)
    for name, value in (
        ("gpg.format", "ssh"),
        ("gpg.ssh.program", executable),
        ("user.signingkey", str(key.with_suffix(".pub"))),
        ("gpg.ssh.allowedSignersFile", str(anchor)),
    ):
        git(repo, "config", name, value)


def signature_repository(tmp_path: Path, *, coupled: bool = False) -> tuple[Path, str, Path]:
    repo = init_git_repo(tmp_path / "repo")
    (repo / ".ethos").mkdir()
    (repo / ".ethos/profile.toml").write_text('profile_id = "signature-fixture"\n')
    (repo / ".ethos/workspace.toml").write_text(
        render_branch_policy(
            release_branch="main",
            accepted_branch="dev",
            candidate_branch="candidate/dev",
            work_branch_prefix="work/",
            proposal_branch_prefix="proposal/",
            release_mirror="accepted_ff" if coupled else "independent",
        )
        + '\n[commit_policy]\nsubject_pattern = "^fix: .+"\n'
        + 'signing_required = true\nsigning_format = "ssh"\n'
    )
    git(repo, "add", ".ethos")
    git(repo, "commit", "-m", "fix: accepted signing policy")
    old = git(repo, "rev-parse", "HEAD")
    git(repo, "branch", "candidate/dev", old)
    git(repo, "branch", "main", old)
    candidate = tmp_path / "candidate"
    git(repo, "worktree", "add", str(candidate), "candidate/dev")
    configure_signer(repo, tmp_path)
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
