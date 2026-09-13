"""Minimal signed-object fixtures for public publication behavior."""

from __future__ import annotations

import hashlib
import subprocess
from typing import TYPE_CHECKING

from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import apply_accepted_closeout
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import seed_executed_proof

if TYPE_CHECKING:
    from pathlib import Path

PROPOSAL = "terminal-convergence"
PROPOSAL_REF = f"refs/heads/proposal/{PROPOSAL}"


def branch_publication_fixture(
    tmp_path: Path,
    *,
    source_branch: str = "candidate/dev",
    object_format: str = "sha1",
    proof: bool = True,
) -> tuple[Path, dict[str, Path], str]:
    repo = init_git_repo(tmp_path / "proposal-repo", object_format=object_format)
    adopt_and_commit(repo)
    configure_publication_signer(repo, tmp_path)
    (repo / "proposal.txt").write_text("signed proposal source\n", encoding="utf-8")
    git(repo, "add", "proposal.txt")
    git(repo, "commit", "-m", "feat: sign proposal source")
    head = git(repo, "rev-parse", "HEAD")
    if source_branch != "dev":
        git(repo, "branch", source_branch, head)
        git(repo, "checkout", source_branch)
    if proof:
        seed_executed_proof(repo, head)
    remotes: dict[str, Path] = {}
    for peer_id, remote in (("gitlab", "origin"), ("github", "github")):
        target = tmp_path / f"{peer_id}.git"
        git(tmp_path, "init", "--bare", f"--object-format={object_format}", target.as_posix())
        git(repo, "remote", "add", remote, target.as_posix())
        git(repo, "push", remote, "HEAD:refs/heads/dev")
        remotes[peer_id] = target
    return repo, remotes, head


def branch_publication(
    repo: Path,
    head: str | None,
    *args: str,
    blocked: bool = False,
    target_ref: str = PROPOSAL_REF,
):
    command = ["publish", "--ref", target_ref, "--probe-remote", *args]
    if head is not None:
        command += ["--expect-head", head]
    runner = run_ethos_blocked if blocked or head is None else run_ethos
    return runner(*command, "--json", cwd=repo)


def apply_receipt(repo: Path, receipt: dict[str, object], head: str, *, blocked: bool = False):
    runner = run_ethos_blocked if blocked else run_ethos
    return runner(
        "publish",
        "--receipt",
        str(receipt["path"]),
        "--receipt-sha256",
        str(receipt["sha256"]),
        "--apply",
        "--authorize",
        "--expect-head",
        head,
        "--json",
        cwd=repo,
    )


def proposal_ref(remote: Path) -> str:
    return git(remote, "for-each-ref", "--format=%(objectname)", PROPOSAL_REF)


def configure_publication_signer(repo: Path, root: Path) -> tuple[Path, str]:
    key = root / "publication-signer"
    subprocess.run(
        ("/usr/bin/ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", key.as_posix()),
        check=True,
        capture_output=True,
        text=True,
    )
    public = key.with_suffix(".pub")
    fingerprint = subprocess.run(
        ("/usr/bin/ssh-keygen", "-lf", public.as_posix(), "-E", "sha256"),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()[1]
    anchor = root / "allowed-signers"
    anchor.write_text(
        f'test@example.com namespaces="git" {public.read_text(encoding="utf-8").strip()}\n',
        encoding="utf-8",
    )
    anchor.chmod(0o600)
    for name, value in (
        ("gpg.format", "ssh"),
        ("gpg.ssh.program", "/usr/bin/ssh-keygen"),
        ("gpg.ssh.allowedSignersFile", anchor.as_posix()),
        ("user.signingkey", public.as_posix()),
        ("user.email", "test@example.com"),
        ("commit.gpgsign", "true"),
    ):
        git(repo, "config", name, value)
    return anchor, fingerprint


def signed_publication_fixture(
    tmp_path: Path,
) -> tuple[Path, dict[str, Path], str, str, str, str, str]:
    repo = init_git_repo(tmp_path / "publication-repo")
    adopt_and_commit(repo)
    accepted_before = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-b", "candidate/dev")
    anchor, fingerprint = configure_publication_signer(repo, tmp_path)
    release = repo / ".ethos/release.toml"
    release.write_text(
        '[protected_refs]\nbranches = ["main", "dev"]\ntags = ["v*"]\n\n'
        + release.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (repo / "VERSION").write_text("1.2.3\n", encoding="ascii")
    (repo / "release.txt").write_text("release\n", encoding="utf-8")
    git(repo, "add", ".ethos/release.toml", "VERSION", "release.txt")
    git(repo, "commit", "-m", "feat: publish exact local object")
    commit = git(repo, "rev-parse", "HEAD")
    tree = git(repo, "rev-parse", "HEAD^{tree}")
    seed_executed_proof(repo, commit)
    apply_accepted_closeout(repo, accepted_before, commit)
    git(repo, "tag", "-s", "-m", "release v1.2.3", "v1.2.3")
    tag = git(repo, "rev-parse", "refs/tags/v1.2.3")
    remotes: dict[str, Path] = {}
    for peer_id, remote in (("gitlab", "origin"), ("github", "github")):
        target = tmp_path / f"publication-{peer_id}.git"
        git(tmp_path, "init", "--bare", target.as_posix())
        git(repo, "remote", "add", remote, target.as_posix())
        remotes[peer_id] = target
    return (
        repo,
        remotes,
        commit,
        tag,
        tree,
        fingerprint,
        hashlib.sha256(anchor.read_bytes()).hexdigest(),
    )
