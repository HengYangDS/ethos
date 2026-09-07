"""Create repository commits through the declared subject and signing policy."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from ethos.adapters.repo.commit.admission import commit_policy_report
from ethos.adapters.repo.commit.admission import commit_subject_gap
from ethos.adapters.repo.git import run_git
from ethos.repository.policy.commit import load_commit_policy

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


def commit_environment(root: Path, environment: Mapping[str, str] | None) -> dict[str, str]:
    """Return the explicit Git configuration for one required signed commit."""
    bound = dict(environment or {})
    signing = run_git(root, "config", "--local", "--get", "user.signingkey", check=False)
    if signing.returncode:
        message = "git_effect_signing_key_invalid"
        raise ValueError(message)
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
    for name, value in (
        ("commit.gpgSign", "true"),
        ("gpg.format", "ssh"),
        *signing_inputs,
        ("user.signingkey", signing_value),
    ):
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
    environment: Mapping[str, str] | None = None,
    runner: Callable[..., Any] = run_git,
) -> Any:
    """Create and verify one commit object under repository signing policy."""
    policy = load_commit_policy(root)
    if gap := commit_subject_gap(policy, message):
        raise ValueError(gap)
    sign = policy is not None and policy.signing_required
    completed = runner(
        root,
        "commit-tree",
        *(("-S",) if sign else ()),
        tree,
        "-p",
        parent,
        "-m",
        message,
        check=False,
        env=commit_environment(root, environment) if sign else environment,
    )
    if completed.returncode or not sign:
        return completed
    revision = completed.stdout.strip()
    gaps = (
        cast(
            "list[str]",
            commit_policy_report(root, policy, revision, verify_trust=True)["required_gaps"],
        )
        if revision
        else ["git_effect_signed_commit_missing"]
    )
    if revision and not gaps:
        return completed
    return subprocess.CompletedProcess(
        completed.args,
        1,
        completed.stdout,
        gaps[0],
    )
