"""Repository-declared commit-message admission."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path
from typing import Literal
from typing import NotRequired
from typing import TypedDict

from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import run_command
from ethos.repository.profile import load_repository_profile

LifecycleAction = Literal["archive", "materialize", "start"]


class CommitMessageReport(TypedDict):
    """Closed commit-message admission result."""

    verdict: Literal["pass", "block"]
    state: Literal["admitted", "blocked"]
    hook: Literal["commit-msg"]
    required_gaps: list[str]
    decision: NotRequired[dict[str, str]]
    exit_code: NotRequired[int]
    stdout: NotRequired[str]
    stderr: NotRequired[str]


def validate_commit_message(root: Path, message: Path) -> CommitMessageReport:
    """Execute the repository's one declared validator against one exact file."""
    repo = root.resolve()
    target = message.resolve()
    if not target.is_file():
        return _blocked("commit_message_path_invalid")
    return _execute_validator(repo, target)


def validate_commit_message_text(root: Path, message: str) -> CommitMessageReport:
    """Execute the repository's validator against one in-memory message."""
    common = Path(git_common_dir(root))
    directory = common / "ethos" / "transactions"
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=directory,
        prefix="commit-message-",
        suffix=".txt",
    ) as stream:
        stream.write(message.rstrip("\n") + "\n")
        stream.flush()
        return _execute_validator(root.resolve(), Path(stream.name))


def lifecycle_commit_subject(root: Path, action: LifecycleAction, change: str) -> str:
    """Generate and admit one lifecycle subject through repository policy."""
    subject = f"chore(openspec): {action} {change}"
    report = validate_commit_message_text(root, subject)
    if report["verdict"] != "pass":
        raise ValueError(str(report["required_gaps"][0]))
    return subject


def _execute_validator(repo: Path, target: Path) -> CommitMessageReport:
    profile = load_repository_profile(repo)
    if profile.state == "invalid":
        return _blocked("repository_profile_invalid:.ethos/profile.toml")
    declaration = profile.declaration
    policy = declaration.commit_message if declaration else None
    if policy is None:
        return _blocked("commit_message_policy_missing")
    missing = tuple(path for path in policy.locked_inputs if not (repo / path).is_file())
    if missing:
        return _blocked(f"commit_message_locked_input_missing:{missing[0]}")
    command = tuple(_argument(token, target) for token in policy.command)
    executable = _executable(command[0])
    if executable is None:
        return _blocked("commit_message_validator_unavailable")
    completed = run_command(repo, (executable, *command[1:]))
    if completed.returncode:
        return {
            **_blocked("commit_message_policy_rejected"),
            "exit_code": completed.returncode,
            "stdout": completed.stdout[-4096:],
            "stderr": completed.stderr[-4096:],
        }
    return {
        "verdict": "pass",
        "state": "admitted",
        "hook": "commit-msg",
        "required_gaps": [],
    }


def _argument(token: str, message: Path) -> str:
    return message.as_posix() if token == "{message}" else token


def _executable(command: str) -> str | None:
    if command in {"python", "python3"}:
        return sys.executable
    return shutil.which(command)


def _blocked(gap: str) -> CommitMessageReport:
    return {
        "verdict": "block",
        "state": "blocked",
        "hook": "commit-msg",
        "decision": {"action": "block", "reason": gap},
        "required_gaps": [gap],
    }
