"""Minimal signed-object fixtures for public publication behavior."""

from __future__ import annotations

import hashlib
import os
from typing import TYPE_CHECKING

from ethos.adapters.repo.commit.creation import configured_signer_fingerprint
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.schema import state_database
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import apply_accepted_closeout
from tests.support.governed_repository import exact_lease
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_active_commitment
from tests.support.proof import seed_executed_proof
from tests.support.signature import configure_signer

if TYPE_CHECKING:
    from pathlib import Path

PROPOSAL = "terminal-convergence"
PROPOSAL_REF = f"refs/heads/proposal/{PROPOSAL}"


def publication_peers(repo: Path, root: Path, *refs: str, object_format: str = "sha1"):
    """Create two independent native peers with the caller's exact initial refs."""
    peers = {}
    for peer_id, remote in (("gitlab", "origin"), ("github", "github")):
        target = root / f"{peer_id}.git"
        git(root, "init", "--bare", f"--object-format={object_format}", str(target))
        git(repo, "remote", "add", remote, str(target))
        if refs:
            git(repo, "push", remote, *refs)
        peers[peer_id] = target
    return peers


def branch_publication_fixture(
    tmp_path: Path,
    *,
    source_branch: str = "candidate/dev",
    object_format: str = "sha1",
    proof: bool = True,
    accepted: bool = False,
    peer_ids: tuple[str, ...] = ("gitlab", "github"),
) -> tuple[Path, dict[str, Path], str]:
    repo = init_git_repo(tmp_path / "proposal-repo", object_format=object_format)
    adopt_and_commit(repo)
    if peer_ids == ("gitlab",):
        release = repo / ".ethos/release.toml"
        release.write_text(release.read_text().rsplit("[[publication.peers]]", 1)[0])
    baseline = git(repo, "rev-parse", "HEAD")
    configure_signer(repo, tmp_path)
    git(repo, "config", "commit.gpgsign", "true")
    if accepted:
        git(repo, "checkout", "-b", "candidate/dev")
    (repo / "proposal.txt").write_text("signed proposal source\n", encoding="utf-8")
    git(repo, "add", "proposal.txt", ".ethos/release.toml")
    git(repo, "commit", "-m", "feat: sign proposal source")
    head = git(repo, "rev-parse", "HEAD")
    if proof or accepted:
        seed_executed_proof(repo, head)
    if accepted:
        apply_accepted_closeout(repo, baseline, head)
        repo = repo.parent / f"{repo.name}-accepted"
    elif source_branch != "dev":
        git(repo, "branch", source_branch, head)
        git(repo, "checkout", source_branch)
    remotes = publication_peers(repo, tmp_path, "HEAD:refs/heads/dev", object_format=object_format)
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


def accepted_release_fixture(
    tmp_path: Path,
    object_format: str = "sha1",
    *,
    native_version: str = "package.json",
    retired_source: bool = False,
):
    repo = init_git_repo(tmp_path / "repo", object_format=object_format)
    adopt_and_commit(repo)
    old = git(repo, "rev-parse", "HEAD")
    git(repo, "branch", "main", old)
    git(repo, "checkout", "-b", "candidate/dev")
    configure_signer(repo, tmp_path)
    git(repo, "config", "commit.gpgsign", "true")
    # This unsigned accepted ancestor predates the newly declared signing policy.
    (repo / "legacy").write_text("pre-adoption source\n")
    git(repo, "add", "legacy")
    git(repo, "-c", "commit.gpgsign=false", "commit", "-m", "legacy accepted source")
    release = repo / ".ethos/release.toml"
    release.write_text(
        '[protected_refs]\nbranches = ["main", "dev"]\ntags = ["v*"]\n\n' + release.read_text()
    )
    workspace = repo / ".ethos/workspace.toml"
    workspace.write_text(
        workspace.read_text()
        + '\n[commit_policy]\nsubject_pattern = "^fix: .+"\n'
        + 'signing_required = true\nsigning_format = "ssh"\n'
    )
    (repo / native_version).write_text(
        "1.2.3\n" if native_version == "VERSION" else '{"name":"sample","version":"1.2.3"}\n'
    )
    if retired_source:
        write_active_commitment(repo)
        git(repo, "add", "openspec")
    git(repo, "add", ".ethos", native_version)
    git(repo, "commit", "-m", "fix: accept native release source")
    head = git(repo, "rev-parse", "HEAD")
    source = repo
    if retired_source:
        source = tmp_path / "authoring"
        git(repo, "worktree", "add", "-b", "work/release", str(source), head)
        acquire_lease(
            state_database(repo),
            lease=exact_lease(branch="work/release", holder_ref=os.environ["ETHOS_ACTOR"]),
        )
    seed_executed_proof(source, head)
    apply_accepted_closeout(repo, old, head)
    accepted = repo.parent / f"{repo.name}-accepted"
    if retired_source:
        run_ethos(
            "lane",
            "retire",
            "landed",
            "--branch",
            "work/release",
            "--expect-head",
            head,
            "--authorize",
            "--apply",
            "--json",
            cwd=accepted,
        )
        assert not source.exists()
    main = tmp_path / "release"
    git(repo, "worktree", "add", str(main), "main")
    return accepted, main, old, head


def signed_publication_fixture(
    tmp_path: Path,
) -> tuple[Path, dict[str, Path], str, str, str, str, str]:
    repo, _main, _old, commit = accepted_release_fixture(tmp_path, native_version="VERSION")
    anchor = tmp_path / "trust/allowed-signers"
    git(repo, "tag", "-s", "-m", "release v1.2.3", "v1.2.3")
    return (
        repo,
        publication_peers(repo, tmp_path),
        commit,
        git(repo, "rev-parse", "refs/tags/v1.2.3"),
        git(repo, "rev-parse", "HEAD^{tree}"),
        configured_signer_fingerprint(repo),
        hashlib.sha256(anchor.read_bytes()).hexdigest(),
    )
