"""Observe and admit prospective and existing repository commits."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_object import observe_commit
from ethos.adapters.repo.trust_anchor.verification import verify_commit_trust
from ethos.contracts.paradigm.declaration import binding_path
from ethos.contracts.paradigm.declaration import load_repository_paradigm
from ethos.repository.policy.commit import commit_policy_from_text

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from ethos.repository.policy.commit import CommitPolicy

_POLICY_PATH = binding_path("workspace")
# Git removes everything below this line, where `git commit --verbose` places the staged diff.
_SCISSORS = re.compile(r"^\S+ -{24} >8 -{24}$", re.MULTILINE)


def _indexed_commit_policy(
    root: Path, *, index_env: Mapping[str, str] | None = None
) -> CommitPolicy:
    """Compile commit policy from the exact prospective Git index tree."""
    listed = run_git(
        root,
        "ls-files",
        "--stage",
        "-z",
        "--",
        _POLICY_PATH,
        check=False,
        observation=index_env is None,
        env=index_env,
        text=False,
    )
    if listed.returncode != 0:
        message = "commit_policy_index_unreadable"
        raise ValueError(message)
    records = tuple(record for record in listed.stdout.split(b"\0") if record)
    if not records:
        return commit_policy_from_text("")
    if len(records) != 1:
        message = "commit_policy_index_unmerged"
        raise ValueError(message)
    metadata, separator, path = records[0].partition(b"\t")
    fields = metadata.split()
    if separator != b"\t" or path != _POLICY_PATH.encode() or len(fields) != 3:
        message = "commit_policy_index_invalid"
        raise ValueError(message)
    mode, object_id, stage = fields
    if stage != b"0":
        message = "commit_policy_index_unmerged"
        raise ValueError(message)
    if mode not in {b"100644", b"100755"}:
        message = "commit_policy_index_invalid"
        raise ValueError(message)
    return commit_policy_from_text(
        _blob_text(root, object_id.decode("ascii"), gap="commit_policy_index_unreadable")
    )


def commit_message_report(
    root: Path, message_file: Path, *, index_env: Mapping[str, str] | None = None
) -> dict[str, object]:
    """Validate the final commit message above Git's scissors line against the index policy."""
    path = message_file if message_file.is_absolute() else root / message_file
    try:
        message = _SCISSORS.split(path.read_text(encoding="utf-8"), maxsplit=1)[0]
    except (OSError, UnicodeError):
        return _blocked("commit_message_unreadable")
    candidate = _indexed_commit_policy(root, index_env=index_env)
    head = peel_commit(root, "HEAD")
    incumbent = commit_policy_for_revision(root, head) if head else candidate
    gaps = []
    for policy in dict.fromkeys((candidate, incumbent)):
        gaps.extend(commit_message_gaps(policy, message))
        gaps.extend(prospective_identity_gaps(root, policy))
    if gaps:
        return {**_blocked(gaps[0]), "required_gaps": list(dict.fromkeys(gaps))}
    return _passed("subject_admitted")


def prospective_identity_gaps(
    root: Path, policy: CommitPolicy, *, environment: dict[str, str] | None = None
) -> list[str]:
    """Read effective Git identities at the same environment as commit creation."""
    identities: dict[str, object] = {}
    for role in ("author", "committer"):
        if getattr(policy, role) is None:
            continue
        observed = run_git(root, "var", f"GIT_{role.upper()}_IDENT", check=False, env=environment)
        identity, separator, _time = observed.stdout.strip().rpartition("> ")
        name, opening, email = identity.rpartition(" <")
        if observed.returncode or not separator or not opening:
            return [f"commit_{role}_identity_unavailable"]
        identities[role] = {"name": name, "email": email}
    return policy.identity_gaps(identities)


def commit_message_gaps(
    policy: CommitPolicy, message: str, *, subject: str | None = None, revision: str = ""
) -> list[str]:
    """Judge a whole message: no private-class address anywhere, then the subject grammar.

    The address gap replaces the subject gap, which would repeat the subject's text.
    """
    if load_repository_paradigm().names_private_address(message):
        return ["commit_message_private_address" + (f":{revision}" if revision else "")]
    gap = commit_subject_gap(policy, message if subject is None else subject, revision=revision)
    return [gap] if gap else []


def commit_subject_gap(
    policy: CommitPolicy,
    subject: str,
    *,
    revision: str = "",
) -> str:
    """Return the canonical subject-policy gap for one prospective or existing commit."""
    first_line = subject.partition("\n")[0]
    if policy.accepts_subject(first_line):
        return ""
    coordinate = f"{revision}:" if revision else ""
    return f"commit_subject_invalid:{coordinate}{first_line}"


def commit_policy_report(
    root: Path,
    policy: CommitPolicy,
    revision: str = "HEAD",
    *,
    verify_trust: bool = True,
) -> dict[str, object]:
    """Observe and admit one object under an explicitly selected authority policy."""
    observation = observe_commit(root, revision)
    report = evaluate_commit_policy(policy, observation, revision)
    signature = cast("dict[str, object]", report["signature"])
    if verify_trust and not signature["required_gaps"]:
        trust = verify_commit_trust(root, str(observation.get("object_oid") or revision))
        trust_gaps = [str(gap) for gap in cast("list[object]", trust.get("required_gaps", []))]
        signature.update(
            verification=trust,
            verification_state="rejected" if trust_gaps else "verified",
        )
        gaps = cast("list[str]", report["required_gaps"])
        gaps.extend(trust_gaps)
        report["verdict"] = "block" if gaps else "pass"
    return report


def evaluate_commit_policy(
    policy: CommitPolicy,
    observation: Mapping[str, object],
    revision: str,
) -> dict[str, object]:
    """Purely judge supplied facts; neither observe Git nor verify signature trust."""
    object_oid = str(observation.get("object_oid") or revision)
    subject = str(observation.get("subject") or "")
    head = {
        key: observation.get(key, {}) for key in ("object_oid", "subject", "author", "committer")
    }
    gaps = [str(gap) for gap in cast("list[object]", observation.get("required_gaps", []))]
    if not gaps:
        message = str(observation.get("message") or subject)
        gaps.extend(commit_message_gaps(policy, message, subject=subject, revision=object_oid))
    gaps.extend(policy.identity_gaps(head, revision=object_oid))
    signature = _signature_policy_report(
        policy,
        object_oid,
        cast("dict[str, object]", observation.get("signature", {})),
    )
    gaps.extend(cast("list[str]", signature["required_gaps"]))
    return {
        "verdict": "block" if gaps else "pass",
        "state": str(observation.get("state") or "unknown"),
        "head": head,
        "signature": signature,
        "required_gaps": gaps,
    }


def _signature_policy_report(
    policy: CommitPolicy,
    revision: str,
    facts: dict[str, object],
) -> dict[str, object]:
    present = facts.get("present") is True
    observed_format = str(facts.get("format") or "")
    gaps: list[str] = []
    state = "present"
    if not present:
        state = "missing"
        gaps.append(f"commit_signature_missing:{revision}")
    elif observed_format != policy.signing_format:
        state = "format_mismatch"
        gaps.append(
            "commit_signature_format_mismatch:"
            f"{revision}:expected={policy.signing_format}:"
            f"observed={observed_format or 'unknown'}"
        )
    return {
        "verdict": "block" if gaps else "pass",
        "state": state,
        "present": present,
        "format": observed_format,
        "required_gaps": gaps,
    }


def peel_commit(root: Path, revision: str) -> str:
    completed = run_git(
        root,
        "rev-parse",
        "--verify",
        f"{revision}^{{commit}}",
        check=False,
        observation=True,
    )
    return completed.stdout.strip() if completed.returncode == 0 else ""


def commit_policy_for_revision(root: Path, proposed_commit: str) -> CommitPolicy:
    """Compile an exact Git-tree policy; an absent binding yields the paradigm's policy."""
    listed = run_git(
        root,
        "ls-tree",
        "-z",
        proposed_commit,
        "--",
        _POLICY_PATH,
        check=False,
        observation=True,
        text=False,
    )
    if listed.returncode != 0:
        message = f"commit_policy_projection_unreadable:{proposed_commit}"
        raise ValueError(message)
    records = tuple(record for record in listed.stdout.split(b"\0") if record)
    if not records:
        return commit_policy_from_text("")
    if len(records) != 1:
        message = f"commit_policy_projection_invalid:{proposed_commit}"
        raise ValueError(message)
    metadata, separator, path = records[0].partition(b"\t")
    fields = metadata.split()
    if (
        separator != b"\t"
        or path != _POLICY_PATH.encode()
        or len(fields) != 3
        or fields[0] not in {b"100644", b"100755"}
        or fields[1] != b"blob"
    ):
        message = f"commit_policy_projection_invalid:{proposed_commit}"
        raise ValueError(message)
    return commit_policy_from_text(
        _blob_text(
            root,
            fields[2].decode("ascii"),
            gap=f"commit_policy_projection_unreadable:{proposed_commit}",
        )
    )


def _blob_text(root: Path, object_id: str, *, gap: str) -> str:
    completed = run_git(
        root,
        "cat-file",
        "blob",
        object_id,
        check=False,
        observation=True,
        text=False,
    )
    if completed.returncode != 0:
        raise ValueError(gap)
    try:
        return completed.stdout.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(gap) from error


def _passed(state: str) -> dict[str, object]:
    return {"verdict": "pass", "state": state, "hook": "commit-msg", "required_gaps": []}


def _blocked(gap: str) -> dict[str, object]:
    return {
        "verdict": "block",
        "state": "blocked",
        "hook": "commit-msg",
        "required_gaps": [gap],
    }
