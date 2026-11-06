"""Resolve a peer's forge web repository from local connection metadata only.

Tracked configuration never carries a peer's coordinates. A local
`remote.<name>.forgeRepository` key is authoritative when present; otherwise an `http` or
`https` Git remote without userinfo names the repository. Nothing else is guessed: an SSH or
scp-like remote stays unresolved, and a refused value is never repeated.
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from ethos.adapters.repo.git import git_stdout

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class ForgeWebRepository:
    """One peer's web repository URL, or the gap and the local action that resolves it."""

    url: str = ""
    gap: str = ""
    next_action: str = ""


def forge_web_repository(root: Path, remote: str) -> ForgeWebRepository:
    """Use the local key exactly, else a credential-free http(s) remote without `/` or `.git`."""
    key = git_stdout(root, "config", "--local", "--get", f"remote.{remote}.forgeRepository")
    if key:
        return ForgeWebRepository(url=key) if _valid(key) else _gap("invalid", remote)
    url = git_stdout(root, "remote", "get-url", remote)
    try:
        parts = urlsplit(url)
    except ValueError:
        return _gap("unresolved", remote)
    if parts.scheme not in {"http", "https"}:
        return _gap("unresolved", remote)
    if "@" in parts.netloc:
        return _gap("credentialed", remote)
    candidate = url.removesuffix("/").removesuffix(".git")
    return ForgeWebRepository(url=candidate) if _valid(candidate) else _gap("unresolved", remote)


def _valid(value: str) -> bool:
    """Admit an http(s) URL with a host, at least a namespace and a project, and nothing else."""
    try:
        url = urlsplit(value)
        return (
            value == value.strip()
            and url.scheme in {"http", "https"}
            and bool(url.hostname)
            and url.port != 0
            and not (url.username or url.password or url.query or url.fragment)
            and len(tuple(filter(None, url.path.split("/")))) >= 2
        )
    except ValueError:
        return False


def _gap(kind: str, remote: str) -> ForgeWebRepository:
    """Name the refusal and the value-free local command an operator completes."""
    setting = shlex.join(("git", "config", "--local", f"remote.{remote}.forgeRepository"))
    return ForgeWebRepository(
        gap=f"forge_repository_{kind}:{remote}", next_action=f"{setting} <web-url>"
    )
