"""Compile the repository commit policy: the paradigm's grammar and SSH signature.

A tracked `[commit_policy]` may restrict scopes and constrain identities. The paradigm
fixes the signature, so a binding that still declares a signing field restates it; the
paradigm report names that field and no reader consults its value.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Literal

from ethos.contracts.paradigm.declaration import load_repository_paradigm

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

RETIRED_COMMIT_POLICY_FIELDS = ("signing_required", "signing_format")
_FIELDS = frozenset({"subject_pattern", "scopes", "author", "committer"})


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
    """One strictly validated repository commit policy; every commit carries its signature."""

    subject_pattern: str
    signing_format: Literal["ssh"]
    scopes: tuple[str, ...] = ()
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
            "signing_format": self.signing_format,
            **({"scopes": list(self.scopes)} if self.scopes else {}),
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


def _scopes(raw: dict[str, object]) -> tuple[str, ...]:
    """Read the optional scope list that restricts the shared commit grammar."""
    if "scopes" not in raw:
        return ()
    value = raw["scopes"]
    scope = re.compile(load_repository_paradigm().commit.scope)
    if (
        "subject_pattern" in raw
        or not isinstance(value, list)
        or not value
        or any(not isinstance(name, str) or not scope.fullmatch(name) for name in value)
        or len(set(value)) != len(value)
    ):
        message = "commit_policy_invalid:scopes"
        raise ValueError(message)
    return tuple(value)


def _subject_pattern(raw: dict[str, object], scopes: tuple[str, ...]) -> str:
    """Return a declared subject pattern, or the shared grammar the paradigm defines."""
    if "subject_pattern" not in raw:
        return load_repository_paradigm().commit.subject_pattern(scopes)
    subject_pattern = _required_text(raw, "subject_pattern")
    try:
        re.compile(subject_pattern)
    except re.error as error:
        message = f"commit_policy_subject_pattern_invalid:{error}"
        raise ValueError(message) from error
    return subject_pattern


def commit_policy_from_text(text: str) -> CommitPolicy:
    """Compile an already-observed binding; an absent table yields the paradigm's policy."""
    try:
        payload = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        message = f"commit_policy_toml_invalid:{error}"
        raise ValueError(message) from error
    raw = payload.get("commit_policy", {})
    if not isinstance(raw, dict):
        message = "commit_policy_invalid:must_be_table"
        raise TypeError(message)
    unknown = sorted(set(raw) - _FIELDS - set(RETIRED_COMMIT_POLICY_FIELDS))
    if unknown:
        message = f"commit_policy_unknown_fields:{','.join(unknown)}"
        raise ValueError(message)
    scopes = _scopes(raw)
    return CommitPolicy(
        subject_pattern=_subject_pattern(raw, scopes),
        signing_format=load_repository_paradigm().commit.signature,
        scopes=scopes,
        author=_identity(raw, "author"),
        committer=_identity(raw, "committer"),
    )


def load_commit_policy(root: Path) -> CommitPolicy:
    """Compile the commit policy the working tree's binding selects."""
    path = root / ".ethos" / "workspace.toml"
    return commit_policy_from_text(path.read_text(encoding="utf-8") if path.exists() else "")
