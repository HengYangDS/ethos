"""Signed adopted-repository fixture for package delivery proof."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import run_command

if TYPE_CHECKING:
    from pathlib import Path

CommandRunner = Callable[..., str]


def _required_executable(name: str) -> str:
    executable = shutil.which(name)
    if executable is None:
        message = f"required executable is unavailable: {name}"
        raise RuntimeError(message)
    return executable


def _configure_product_signer(root: Path, *, git: str, run: CommandRunner) -> None:
    ssh_keygen = _required_executable("ssh-keygen")
    signer = root.parent / "product-signer"
    trust_anchor = root.parent / "allowed-signers"
    run(ssh_keygen, "-q", "-t", "ed25519", "-N", "", "-f", str(signer))
    public_key = signer.with_suffix(".pub").read_text(encoding="utf-8").strip()
    trust_anchor.write_text(
        f'ethos-install-smoke@example.invalid namespaces="git" {public_key}\n',
        encoding="utf-8",
    )
    trust_anchor.chmod(0o600)
    for name, value in (
        ("gpg.format", "ssh"),
        ("gpg.ssh.program", ssh_keygen),
        ("gpg.ssh.allowedSignersFile", str(trust_anchor)),
        ("user.signingkey", str(signer)),
        ("commit.gpgsign", "true"),
    ):
        run(git, "config", name, value, cwd=root)


def materialize_adopter(
    root: Path,
    *,
    openspec_config: Path,
    run: CommandRunner,
) -> str:
    """Materialize and commit one signed repository adopted by the installed wheel."""
    git = _required_executable("git")
    run(git, "init", "--quiet", "--initial-branch=dev", str(root))
    run(git, "config", "user.name", "ETHOS Install Smoke", cwd=root)
    run(git, "config", "user.email", "ethos-install-smoke@example.invalid", cwd=root)
    _configure_product_signer(root, git=git, run=run)
    (root / ".ethos").mkdir()
    change = root / "openspec/changes/smoke-change"
    change.mkdir(parents=True)
    (root / ".ethos/profile.toml").write_text(
        'profile_id = "installed-cli-adopter"\n\n[openspec]\nmaterial_paths = ["**"]\n',
        encoding="utf-8",
    )
    dev = root / "dev"
    dev.mkdir()
    for name in ("verify", "install"):
        command = dev / name
        command.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
        command.chmod(0o755)
    (root / ".ethos/release.toml").write_text(
        """[publication]
local_verification_command = "dev/verify"
local_installation_command = "dev/install"

[[publication.peers]]
id = "file"
provider = "git"
role = "package_smoke"
git_remote = "origin"
capabilities = ["repository", "publication"]
""",
        encoding="utf-8",
    )
    shutil.copy2(openspec_config, root / "openspec/config.yaml")
    (change / ".openspec.yaml").write_text("schema: spec-driven\n", encoding="utf-8")
    (change / "proposal.md").write_text(
        "## Why\n\nExercise the installed package lifecycle.\n\n"
        "## What Changes\n\n- Add one package-smoke change.\n\n"
        "## Out of Scope\n\n- Product behavior.\n",
        encoding="utf-8",
    )
    (change / "design.md").write_text(
        "## Context\n\nPackage-only lifecycle proof.\n\n"
        "## Decision\n\nUse only official OpenSpec artifacts.\n",
        encoding="utf-8",
    )
    (change / "tasks.md").write_text(
        "## 1. Package smoke\n\n- [x] 1.1 Exercise installed lifecycle.\n",
        encoding="utf-8",
    )
    spec = change / "specs/package-smoke/spec.md"
    spec.parent.mkdir(parents=True)
    spec.write_text(
        "## ADDED Requirements\n\n"
        "### Requirement: Installed lifecycle\n\n"
        "The installed package SHALL govern an official OpenSpec Change.\n\n"
        "#### Scenario: Package smoke runs\n\n"
        "- **WHEN** the installed lifecycle executes\n"
        "- **THEN** no parallel intent carrier is required\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text("# installed CLI adopter\n", encoding="utf-8")
    peer = root.parent / "publication-peer.git"
    run(git, "init", "--quiet", "--bare", str(peer))
    run(git, "remote", "add", "origin", str(peer), cwd=root)
    run(git, "add", ".", cwd=root)
    run(git, "commit", "--quiet", "-m", "initialize installed CLI adopter", cwd=root)
    return run(git, "rev-parse", "HEAD", cwd=root)


def line_ending_conformance(adopter: Path, *, run: CommandRunner) -> list[str]:
    """Round-trip LF, CRLF, and UTF-8 through Git without text-mode inference."""
    git = _required_executable("git")
    fixtures = {
        "lf": b"portable UTF-8: \xe9\x81\x93\n",
        "crlf": b"portable UTF-8: \xe9\x81\x93\r\n",
    }
    observed: list[str] = []
    for style, payload in fixtures.items():
        relative = f"line-ending-{style}.txt"
        path = adopter / relative
        path.write_bytes(payload)
        run(git, "add", "--", relative, cwd=adopter)
        git_blob = run_command(
            adopter,
            (git, "show", f":{relative}"),
            text=False,
            check=True,
        ).stdout
        if git_blob != payload or path.read_bytes() != payload:
            message = f"portable line-ending round-trip failed: {style}"
            raise RuntimeError(message)
        observed.append(style)
    run(git, "reset", "--quiet", "--", *[f"line-ending-{s}.txt" for s in observed], cwd=adopter)
    for style in observed:
        (adopter / f"line-ending-{style}.txt").unlink()
    return observed
