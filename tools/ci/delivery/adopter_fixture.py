"""Signed adopted-repository fixture for package delivery proof."""

from __future__ import annotations

import json
import shutil
import tomllib
from collections.abc import Callable
from typing import TYPE_CHECKING

import tomli_w

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


def commitment_carrier(
    wheel: Path,
    python: Path,
    *,
    commitment_id: str,
    intent: str,
    subjects: tuple[str, ...],
    scope: tuple[str, ...],
    run: CommandRunner,
) -> str:
    """Derive one strict Commitment carrier from the packaged semantic vector."""
    vector = json.loads(
        run(
            str(python),
            "-I",
            "-c",
            "import importlib.resources,sys; "
            "sys.path.insert(0, sys.argv[1]); "
            "print(importlib.resources.files('ethos').joinpath("
            "'data/semantic-contract/vectors.json').read_text())",
            str(wheel),
        )
    )
    payload = tomllib.loads(vector["commitment"]["carrier_toml"])
    required = ("id", "intent", "subjects", "scope", "dependencies")
    if not all(key in payload for key in required):
        message = "packaged semantic contract vector has no structured commitment fields"
        raise RuntimeError(message)
    payload.update(id=commitment_id, intent=intent, subjects=list(subjects), scope=list(scope))
    for key, value in payload.items():
        if (
            key not in {"subjects", "scope"}
            and isinstance(value, list)
            and all(isinstance(item, str) for item in value)
        ):
            payload[key] = []
    return tomli_w.dumps(payload)


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
    wheel: Path,
    python: Path,
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
    (root / ".ethos/commitment.toml").write_text(
        commitment_carrier(
            wheel,
            python,
            commitment_id="repository:installed-cli-adopter",
            intent="Govern the installed CLI adopter.",
            subjects=("repository:installed-cli-adopter",),
            scope=("**",),
            run=run,
        ),
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
    (change / "commitment.toml").write_text(
        commitment_carrier(
            wheel,
            python,
            commitment_id="change:smoke-change",
            intent="Exercise installed CLI repository binding.",
            subjects=("repository:installed-cli-adopter",),
            scope=("README.md",),
            run=run,
        ),
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
