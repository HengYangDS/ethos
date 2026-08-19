from __future__ import annotations

import hashlib
import subprocess
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.repo.git_object import authorize_configured_commit_signer
from ethos.adapters.repo.git_object import commit_trust_setup_action
from ethos.adapters.repo.git_object import verify_commit_trust
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.literal_cases import literal_case

if TYPE_CHECKING:
    from pathlib import Path


def _signed_target(tmp_path: Path) -> tuple[Path, Path, str]:
    repo = init_git_repo(tmp_path / "repo")
    key = tmp_path / "signer"
    subprocess.run(
        ("/usr/bin/ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)),
        check=True,
        capture_output=True,
        text=True,
    )
    git(repo, "config", "gpg.format", "ssh")
    git(repo, "config", "user.signingkey", key.with_suffix(".pub").as_posix())
    (repo / "target.txt").write_text("signed\n", encoding="utf-8")
    git(repo, "add", "target.txt")
    git(repo, "-c", "commit.gpgsign=true", "commit", "-m", "test: signed target")
    return repo, key.with_suffix(".pub"), git(repo, "rev-parse", "HEAD")


def test_owner_only_external_anchor_is_usable_but_does_not_trust_unknown_signer(
    tmp_path: Path,
) -> None:
    repo, _signer, target = _signed_target(tmp_path)
    trust_root = tmp_path / "trust"
    trust_root.mkdir(mode=0o700)
    anchor = trust_root / "allowed-signers"
    anchor.write_text("", encoding="utf-8")
    anchor.chmod(0o600)
    git(repo, "config", "gpg.ssh.allowedSignersFile", anchor.as_posix())

    report = verify_commit_trust(repo, target)

    assert report["required_gaps"] == ["commit_signature_untrusted"]


def _authorization_case(tmp_path: Path) -> tuple[Path, Path, str, str]:
    repo, _signer, target = _signed_target(tmp_path)
    trust_root = tmp_path / "trust"
    trust_root.mkdir(mode=0o700)
    anchor = trust_root / "allowed-signers"
    anchor.write_text("", encoding="utf-8")
    anchor.chmod(0o600)
    git(repo, "config", "gpg.ssh.allowedSignersFile", anchor.as_posix())
    git(repo, "config", "user.email", "owner@example.com")
    return repo, anchor, target, hashlib.sha256(anchor.read_bytes()).hexdigest()


def test_configured_signer_authorization_is_dry_run_then_explicit_atomic_apply(
    tmp_path: Path,
) -> None:
    repo, anchor, target, digest = _authorization_case(tmp_path)

    ready = authorize_configured_commit_signer(
        repo,
        target,
        expected_anchor_sha256=digest,
        apply=False,
        authorized=False,
    )
    unauthorized = authorize_configured_commit_signer(
        repo,
        target,
        expected_anchor_sha256=digest,
        apply=True,
        authorized=False,
    )

    assert (ready["verdict"], ready["state"]) == ("pass", "ready_to_authorize_signer")
    assert unauthorized["required_gaps"] == ["authorization_required"]
    assert anchor.read_bytes() == b""

    applied = authorize_configured_commit_signer(
        repo,
        target,
        expected_anchor_sha256=digest,
        apply=True,
        authorized=True,
    )

    assert (applied["verdict"], applied["state"]) == ("pass", "signer_authorized")
    assert verify_commit_trust(repo, target)["verdict"] == "pass"
    assert anchor.stat().st_mode & 0o777 == 0o600


def test_commit_signer_trust_command_projects_exact_recovery_action(tmp_path: Path) -> None:
    repo, anchor, target, digest = _authorization_case(tmp_path)

    ready = run_ethos(
        "lane",
        "trust-commit-signer",
        "--target-commit",
        target,
        "--expected-anchor-sha256",
        digest,
        "--root",
        repo.as_posix(),
        "--json",
        cwd=repo,
    )
    blocked = run_ethos_blocked(
        "lane",
        "trust-commit-signer",
        "--target-commit",
        target,
        "--expected-anchor-sha256",
        digest,
        "--apply",
        "--root",
        repo.as_posix(),
        "--json",
        cwd=repo,
    )

    assert (ready["verdict"], ready["state"]) == ("pass", "ready_to_authorize_signer")
    assert ready["next_action"] == (
        "ethos lane trust-commit-signer "
        f"--target-commit {target} --expected-anchor-sha256 {digest} "
        "--authorize --apply --json"
    )
    assert blocked["required_gaps"] == ["authorization_required"]
    assert blocked["next_action"] == commit_trust_setup_action(repo, target)
    assert anchor.read_bytes() == b""

    applied = run_ethos(
        "lane",
        "trust-commit-signer",
        "--target-commit",
        target,
        "--expected-anchor-sha256",
        digest,
        "--authorize",
        "--apply",
        "--root",
        repo.as_posix(),
        "--json",
        cwd=repo,
    )
    assert applied["next_action"] == "rerun the exact blocked identity-repair command"


@pytest.mark.parametrize(
    ("arrange", "expected_gap"),
    literal_case(
        "lanes.lease.test_commit_trust:parametrize:test_configured_signer_authorization_fails_closed:0"
    ),
)
def test_configured_signer_authorization_fails_closed(
    tmp_path: Path,
    arrange: str,
    expected_gap: str,
) -> None:
    repo, anchor, target, digest = _authorization_case(tmp_path)
    if arrange == "stale":
        digest = "0" * 64
    elif arrange == "inside":
        anchor = repo / "allowed-signers"
        anchor.write_text("", encoding="utf-8")
        git(repo, "config", "gpg.ssh.allowedSignersFile", anchor.as_posix())
    else:
        anchor.chmod(0o620)

    report = authorize_configured_commit_signer(
        repo,
        target,
        expected_anchor_sha256=digest,
        apply=True,
        authorized=True,
    )

    assert expected_gap in report["required_gaps"]
    assert anchor.read_bytes() == b""
