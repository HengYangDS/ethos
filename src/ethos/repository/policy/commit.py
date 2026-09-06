"""Compile the repository's optional tracked commit policy."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Literal

if TYPE_CHECKING:
    from pathlib import Path

_FIELDS = frozenset({"subject_pattern", "signing_required", "signing_format"})


@dataclass(frozen=True, slots=True, kw_only=True)
class CommitPolicy:
    """One strictly validated repository commit policy."""

    subject_pattern: str
    signing_required: bool
    signing_format: Literal["ssh"]

    def accepts_subject(self, subject: str) -> bool:
        """Return whether the first message line matches the tracked grammar."""
        return re.fullmatch(self.subject_pattern, subject.partition("\n")[0]) is not None

    def projection(self) -> dict[str, object]:
        """Return the canonical public projection of the declaration."""
        return {
            "subject_pattern": self.subject_pattern,
            "signing_required": self.signing_required,
            "signing_format": self.signing_format,
        }


def _required_text(raw: dict[str, object], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value:
        message = f"commit_policy_invalid:{key}"
        raise ValueError(message)
    return value


def load_commit_policy(root: Path) -> CommitPolicy | None:
    """Compile the optional tracked commit policy, failing closed when present."""
    path = root / ".ethos" / "workspace.toml"
    if not path.exists():
        return None
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        message = f"commit_policy_toml_invalid:{error}"
        raise ValueError(message) from error
    if "commit_policy" not in payload:
        return None
    raw = payload["commit_policy"]
    if not isinstance(raw, dict):
        message = "commit_policy_invalid:must_be_table"
        raise TypeError(message)
    unknown = sorted(set(raw) - _FIELDS)
    if unknown:
        message = f"commit_policy_unknown_fields:{','.join(unknown)}"
        raise ValueError(message)
    subject_pattern = _required_text(raw, "subject_pattern")
    try:
        re.compile(subject_pattern)
    except re.error as error:
        message = f"commit_policy_subject_pattern_invalid:{error}"
        raise ValueError(message) from error
    signing_required = raw.get("signing_required")
    if not isinstance(signing_required, bool):
        message = "commit_policy_invalid:signing_required"
        raise TypeError(message)
    signing_format = _required_text(raw, "signing_format")
    if signing_format != "ssh":
        message = f"commit_policy_signing_format_unsupported:{signing_format}"
        raise ValueError(message)
    return CommitPolicy(
        subject_pattern=subject_pattern,
        signing_required=signing_required,
        signing_format="ssh",
    )
