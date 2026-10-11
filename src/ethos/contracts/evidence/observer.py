"""Exact attempt-supplied observer identity, independent of installation layout."""

from __future__ import annotations

import re
import urllib.request
from dataclasses import asdict
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True, slots=True)
class ObserverIdentity:
    """Bind an immutable runtime to one hash-qualified local wheel requirement."""

    requirement: str
    runtime_digest: str
    wheel_sha256: str

    def __post_init__(self) -> None:
        parsed = urlsplit(self.requirement.removeprefix("ethos @ "))
        if (
            not self.requirement.startswith("ethos @ ")
            or parsed.scheme != "file"
            or parsed.netloc not in {"", "localhost"}
            or parsed.query
            or any(character.isspace() for character in self.requirement[8:])
            or parsed.fragment != f"sha256={self.wheel_sha256}"
            or re.fullmatch(r"[0-9a-f]{64}", self.runtime_digest) is None
            or re.fullmatch(r"[0-9a-f]{64}", self.wheel_sha256) is None
            or not self.wheel.is_absolute()
            or self.wheel.suffix != ".whl"
        ):
            msg = "python_native_observer_requirement_invalid"
            raise ValueError(msg)

    @classmethod
    def from_requirement(cls, requirement: str, runtime_digest: str) -> ObserverIdentity:
        """Derive the wheel digest from the supported hash-qualified requirement."""
        digest = urlsplit(requirement.removeprefix("ethos @ ")).fragment.removeprefix("sha256=")
        return cls(requirement, runtime_digest, digest)

    @property
    def wheel(self) -> Path:
        """Decode the native local path without treating a URI as a filesystem path."""
        return Path(urllib.request.url2pathname(urlsplit(self.requirement[8:]).path))

    def to_payload(self) -> dict[str, str]:
        """Keep the same exact identity in execution and native child records."""
        return asdict(self)
