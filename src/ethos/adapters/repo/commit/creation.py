"""Create repository commits through the declared subject and signing policy."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.process import run_command
from ethos.adapters.repo.commit.admission import commit_policy_report
from ethos.adapters.repo.commit.admission import commit_subject_gap
from ethos.adapters.repo.git import committed_file_text
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_object import commit_payload
from ethos.adapters.repo.git_object import observe_commit
from ethos.repository.policy.commit import commit_policy_from_text
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


def create_signed_replacement(root: Path, revision: str) -> str:
    """Create a trusted signature-only object without moving any repository ref."""
    source = observe_commit(root, revision)
    signature = source.get("signature")
    if source["verdict"] != "pass" or not isinstance(signature, dict) or signature["present"]:
        error = "signature_repair_source_not_unsigned"
        raise ValueError(error)
    policy = commit_policy_from_text(committed_file_text(root, revision, ".ethos/workspace.toml"))
    if policy is None or not policy.signing_required:
        error = "signature_repair_policy_required"
        raise ValueError(error)
    if gap := commit_subject_gap(policy, str(source["subject"]), revision=revision):
        raise ValueError(gap)
    payload = commit_payload(root, revision)
    header, separator, message = payload.partition(b"\n\n")
    if not separator:
        error = "signature_repair_payload_unavailable"
        raise ValueError(error)
    armor = _sign_payload(root, payload)
    signature_header = b"gpgsig-sha256" if len(str(source["object_oid"])) == 64 else b"gpgsig"
    signed = (
        header
        + b"\n"
        + signature_header
        + b" "
        + armor.replace(b"\n", b"\n ")
        + separator
        + message
    )
    created = run_git(
        root, "hash-object", "-w", "-t", "commit", "--stdin", stdin=signed, text=False, check=False
    )
    if created.returncode:
        error = "signature_repair_object_failed:" + created.stderr.decode(errors="replace")
        raise ValueError(error)
    replacement = created.stdout.decode("ascii").strip()
    validation_verdict = "block"
    try:
        gaps = (
            cast(
                "list[str]",
                commit_policy_report(root, policy, replacement, verify_trust=True)["required_gaps"],
            )
            if commit_payload(root, replacement) == payload
            else ["signature_repair_payload_changed"]
        )
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        gaps = [str(error)]
        validation_verdict = "unknown"
    if gaps:
        raise ProcessExecutionError(
            gaps[0],
            reason="signature_repair_object_validation_failed",
            cwd=str(root),
            cause=gaps[0],
            observation={
                "replacement": replacement,
                "refs_changed": False,
                "validation_verdict": validation_verdict,
            },
        )
    return replacement


def _sign_payload(root: Path, payload: bytes) -> bytes:
    """Use Git's configured OpenSSH signing protocol on exact payload bytes."""
    environment = commit_environment(root, None)
    configuration = {
        environment[f"GIT_CONFIG_KEY_{i}"]: environment[f"GIT_CONFIG_VALUE_{i}"]
        for i in range(int(environment["GIT_CONFIG_COUNT"]))
    }
    program = configuration.get("gpg.ssh.program") or shutil.which("ssh-keygen")
    if not program:
        error = "git_effect_signing_program_invalid"
        raise ValueError(error)
    with tempfile.TemporaryDirectory(prefix="ethos-signature-", dir=git_common_dir(root)) as tmp:
        directory = Path(tmp)
        key = configuration["user.signingkey"]
        inline = key.startswith("key::")
        if inline:
            public = directory / "signer.pub"
            public.write_text(key.removeprefix("key::"), encoding="utf-8")
            key = public.as_posix()
        material = directory / "payload"
        material.write_bytes(payload)
        result = run_command(
            root,
            (
                program,
                "-Y",
                "sign",
                "-n",
                "git",
                "-f",
                key,
                *(("-U",) if inline else ()),
                str(material),
            ),
            text=False,
            timeout=30,
            env={"GIT_TERMINAL_PROMPT": "0", "SSH_ASKPASS_REQUIRE": "never"},
            remove_env_prefixes=("GIT_",),
        )
        if result.returncode:
            error = "signature_repair_signing_failed:" + result.stderr.decode(errors="replace")
            raise ValueError(error)
        return material.with_suffix(".sig").read_bytes().replace(b"\r\n", b"\n").rstrip(b"\n")
