"""Bind an exact repository-selected SSH signer to one Git invocation."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import effective_git_config_value
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_object import verify_commit_trust

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Mapping


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
    signer_value = effective_git_config_value(root, "gpg.ssh.program")
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
    signing = effective_git_config_value(root, "commit.gpgsign").strip().lower()
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


def commit_metadata(
    root: Path,
    commit: str,
    *,
    run: Callable[..., Any] = run_git,
) -> dict[str, str] | None:
    """Return exact author and committer metadata for one commit."""
    completed = run(
        root,
        "show",
        "-s",
        "--format=%an%x00%ae%x00%aI%x00%cn%x00%ce%x00%cI",
        commit,
        check=False,
    )
    if completed.returncode:
        return None
    fields = completed.stdout.rstrip("\n").split("\0")
    if len(fields) != 6:
        return None
    author, author_email, authored_at, committer, committer_email, committed_at = fields
    return {
        "GIT_AUTHOR_NAME": author,
        "GIT_AUTHOR_EMAIL": author_email,
        "GIT_AUTHOR_DATE": authored_at,
        "GIT_COMMITTER_NAME": committer,
        "GIT_COMMITTER_EMAIL": committer_email,
        "GIT_COMMITTER_DATE": committed_at,
    }


def existing_commit_replacement(root: Path, old: str, new: str) -> dict[str, str]:
    """Describe one existing same-payload old-to-new commit replacement."""
    metadata, message = _commit_inputs(root, old)
    return _replacement_record(root, old, new, metadata, message)


def create_signed_commit_replacements(
    root: Path, base: str, commits: list[str]
) -> list[dict[str, str]]:
    """Recreate one linear commit sequence under current signing policy."""
    replacements: list[dict[str, str]] = []
    new_parent = base
    for old in commits:
        metadata, message = _commit_inputs(root, old)
        completed = create_git_commit(
            root,
            tree=current_tree(root, old),
            parent=new_parent,
            message=message.decode("utf-8", errors="surrogateescape"),
            preserve_message=True,
            environment=metadata,
        )
        if completed.returncode or not completed.stdout.strip():
            gap = completed.stderr.strip() or "identity_repair_commit_creation_failed"
            message = f"{gap}:{old}"
            raise ValueError(message)
        new = completed.stdout.strip()
        if new == old:
            message = f"identity_repair_commit_identity_unchanged:{old}"
            raise ValueError(message)
        replacements.append(
            _replacement_record(root, old, new, metadata, message, new_parent=new_parent)
        )
        new_parent = new
    return replacements


def _commit_inputs(root: Path, commit: str) -> tuple[dict[str, str], bytes]:
    metadata = commit_metadata(root, commit)
    raw = run_git(root, "cat-file", "commit", commit, check=False, text=False)
    message = raw.stdout.partition(b"\n\n")[2] if raw.returncode == 0 else b""
    if metadata is None or not message:
        error = f"identity_repair_commit_metadata_unreadable:{commit}"
        raise ValueError(error)
    return metadata, message


def _replacement_record(
    root: Path,
    old: str,
    new: str,
    metadata: Mapping[str, str],
    message: bytes,
    *,
    new_parent: str | None = None,
) -> dict[str, str]:
    return {
        "old_commit": old,
        "new_commit": new,
        "old_parent": git_stdout(root, "rev-parse", f"{old}^"),
        "new_parent": new_parent or git_stdout(root, "rev-parse", f"{new}^"),
        "tree": current_tree(root, old),
        "message_sha256": hashlib.sha256(message).hexdigest(),
        **{key.removeprefix("GIT_").lower(): value for key, value in metadata.items()},
    }
