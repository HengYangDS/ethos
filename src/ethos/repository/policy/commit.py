"""Compile the repository's optional tracked commit policy."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Literal

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

_FIELDS = frozenset(
    {"subject_pattern", "signing_required", "signing_format", "author", "committer"}
)


@dataclass(frozen=True, slots=True, kw_only=True)
class CommitIdentity:
    """An explicitly declared attribution, distinct from a cryptographic signer."""

    name: str
    email: str

    def projection(self) -> dict[str, str]:
        """Return exact identity fields without normalization or account inference."""
        return {"name": self.name, "email": self.email}


@dataclass(frozen=True, slots=True, kw_only=True)
class CommitPolicy:
    """One strictly validated repository commit policy."""

    subject_pattern: str
    signing_required: bool
    signing_format: Literal["ssh"]
    author: CommitIdentity | None = None
    committer: CommitIdentity | None = None

    def accepts_subject(self, subject: str) -> bool:
        """Return whether the first message line matches the tracked grammar."""
        return re.fullmatch(self.subject_pattern, subject.partition("\n")[0]) is not None

    def identity_gaps(self, identities: Mapping[str, object], *, revision: str = "") -> list[str]:
        """Compare only explicitly constrained attribution at the shared semantic owner."""
        return [
            f"commit_{role}_identity_mismatch" + (f":{revision}" if revision else "")
            for role in ("author", "committer")
            if (expected := getattr(self, role)) is not None
            and identities.get(role) != expected.projection()
        ]

    def projection(self) -> dict[str, object]:
        """Return the canonical public projection of the declaration."""
        return {
            "subject_pattern": self.subject_pattern,
            "signing_required": self.signing_required,
            "signing_format": self.signing_format,
            **{
                role: identity.projection()
                for role in ("author", "committer")
                if (identity := getattr(self, role)) is not None
            },
        }


def _required_text(raw: dict[str, object], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value:
        message = f"commit_policy_invalid:{key}"
        raise ValueError(message)
    return value


def _identity(raw: dict[str, object], role: str) -> CommitIdentity | None:
    if role not in raw:
        return None
    value = raw[role]
    if (
        not isinstance(value, dict)
        or set(value) != {"name", "email"}
        or any(
            not isinstance(text, str)
            or not text.strip()
            or text != text.strip()
            or any(character in text for character in "\r\n\x00<>")
            for text in value.values()
        )
    ):
        message = f"commit_policy_invalid:{role}"
        raise ValueError(message)
    return CommitIdentity(name=value["name"], email=value["email"])


def commit_policy_from_text(text: str) -> CommitPolicy | None:
    """Compile an already-observed commit policy, failing closed when present."""
    try:
        payload = tomllib.loads(text)
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
        author=_identity(raw, "author"),
        committer=_identity(raw, "committer"),
    )


def load_commit_policy(root: Path) -> CommitPolicy | None:
    """Compile the optional tracked commit policy from the working tree."""
    path = root / ".ethos" / "workspace.toml"
    return commit_policy_from_text(path.read_text(encoding="utf-8") if path.exists() else "")
