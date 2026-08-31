"""Bind an exact repository-selected SSH signer to one Git invocation."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_object import verify_commit_trust

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Mapping


def _config(root: Path, name: str) -> str:
    """Read one effective signing value without command overlays."""
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(
        {
            key: os.environ[key]
            for key in ("GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM", "GIT_CONFIG_NOSYSTEM")
            if key in os.environ
        }
    )
    git = shutil.which("git", path=environment.get("PATH"))
    if git is None:
        return ""
    completed = subprocess.run(
        (str(Path(git).resolve()), "config", "--get", name),
        cwd=root,
        check=False,
        text=True,
        capture_output=True,
        env=environment | {"LC_ALL": "C", "GIT_NO_REPLACE_OBJECTS": "1"},
        shell=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else ""


def commit_environment(root: Path, environment: Mapping[str, str] | None) -> dict[str, str] | None:
    """Return Git config that cannot drift to a different signing key or agent."""
    bound = dict(environment or {})
    signing = run_git(root, "config", "--local", "--get", "user.signingkey", check=False)
    if signing.returncode:
        return bound or None
    key = Path(signing.stdout.strip())
    if not key.is_absolute() or not key.is_file():
        message = "git_effect_signing_key_invalid"
        raise ValueError(message)
    public_key = key.read_text(encoding="utf-8").strip()
    if not public_key.startswith(("ssh-ed25519 ", "ssh-rsa ", "ecdsa-sha2-")):
        message = "git_effect_signing_key_invalid"
        raise ValueError(message)
    signer_value = _config(root, "gpg.ssh.program")
    signing_value = f"key::{public_key}"
    signing_inputs: tuple[tuple[str, str], ...] = ()
    if signer_value:
        signer = Path(signer_value)
        if not signer.is_absolute() or not signer.is_file() or not os.access(signer, os.X_OK):
            message = "git_effect_signing_program_invalid"
            raise ValueError(message)
        signing_value = key.as_posix()
        signing_inputs = (("gpg.ssh.program", signer.as_posix()),)
    count = int(bound.get("GIT_CONFIG_COUNT", "0"))
    for name, value in (("gpg.format", "ssh"), *signing_inputs, ("user.signingkey", signing_value)):
        bound[f"GIT_CONFIG_KEY_{count}"] = name
        bound[f"GIT_CONFIG_VALUE_{count}"] = value
        count += 1
    bound["GIT_CONFIG_COUNT"] = str(count)
    return bound


def create_git_commit(
    root: Path,
    *,
    tree: str,
    parent: str,
    message: str,
    preserve_message: bool = False,
    environment: Mapping[str, str] | None = None,
    runner: Callable[..., Any] = run_git,
) -> Any:
    """Create and verify one commit object under repository signing policy."""
    signing = _config(root, "commit.gpgsign").strip().lower()
    if signing not in {"", "false", "no", "off", "0", "true", "yes", "on", "1"}:
        message = "git_effect_commit_signing_policy_invalid"
        raise ValueError(message)
    sign = signing in {"true", "yes", "on", "1"}
    completed = runner(
        root,
        "commit-tree",
        *(("-S",) if sign else ()),
        tree,
        "-p",
        parent,
        *(("-F", "-") if preserve_message else ("-m", message)),
        check=False,
        env=commit_environment(root, environment) if sign else environment,
        stdin=message if preserve_message else None,
    )
    if completed.returncode or not sign:
        return completed
    revision = completed.stdout.strip()
    trust = verify_commit_trust(root, revision) if revision else {}
    required_gaps = trust.get("required_gaps")
    gaps = required_gaps if isinstance(required_gaps, list) else []
    if revision and not gaps:
        return completed
    return subprocess.CompletedProcess(
        completed.args,
        1,
        completed.stdout,
        str(gaps[0]) if gaps else "git_effect_signed_commit_missing",
    )
