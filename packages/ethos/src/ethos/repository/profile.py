from __future__ import annotations

import tomllib
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from pathlib import Path


DEFAULT_ROOTS = {
    "rules": "rules",
    "docs": "docs",
    "durable_evidence": "evidence",
    "openspec": "openspec",
    "claims": "evidence/claims",
    "agent_skills": ".agents/skills",
    "local_state": ".ethos/state",
}


@dataclass(frozen=True)
class RepositoryProfile:
    root: Path
    exists: bool
    valid: bool
    source: str
    roots: dict[str, str]
    evidence: dict[str, tuple[str, ...]]
    previous_projection: dict[str, str]


def load_repository_profile(root: Path) -> RepositoryProfile:
    repo = root.resolve()
    profile_path = repo / ".ethos" / "profile.toml"
    roots = dict(DEFAULT_ROOTS)
    evidence: dict[str, tuple[str, ...]] = {}
    previous_projection: dict[str, str] = {}
    if not profile_path.exists():
        return RepositoryProfile(
            root=repo,
            exists=False,
            valid=True,
            source="",
            roots=roots,
            evidence=evidence,
            previous_projection=previous_projection,
        )
    try:
        payload = tomllib.loads(profile_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return RepositoryProfile(
            root=repo,
            exists=True,
            valid=False,
            source=".ethos/profile.toml",
            roots=roots,
            evidence=evidence,
            previous_projection=previous_projection,
        )
    raw_roots = payload.get("roots")
    if isinstance(raw_roots, dict):
        for key, value in raw_roots.items():
            if isinstance(value, str) and value:
                roots[str(key)] = value
    raw_evidence = payload.get("evidence")
    if isinstance(raw_evidence, dict):
        for key, value in raw_evidence.items():
            if isinstance(value, list):
                evidence[str(key)] = tuple(str(item) for item in value if str(item))
    raw_previous = payload.get("previous_projection")
    if isinstance(raw_previous, dict):
        previous_projection = {
            str(key): str(value)
            for key, value in raw_previous.items()
            if isinstance(value, str) and value
        }
    return RepositoryProfile(
        root=repo,
        exists=True,
        valid=True,
        source=".ethos/profile.toml",
        roots=roots,
        evidence=evidence,
        previous_projection=previous_projection,
    )


def profile_root(root: Path, key: str) -> Path:
    profile = load_repository_profile(root)
    return profile.root / profile.roots.get(key, DEFAULT_ROOTS[key])


def profile_relative_root(root: Path, key: str) -> str:
    profile = load_repository_profile(root)
    return profile.roots.get(key, DEFAULT_ROOTS[key])


def profile_evidence_roots(root: Path) -> tuple[str, ...]:
    profile = load_repository_profile(root)
    candidates = [
        ".ethos/profile.toml",
        profile.roots["rules"],
        profile.roots["claims"],
        profile.roots["openspec"],
        profile.roots["durable_evidence"],
        profile.roots["docs"],
        DEFAULT_ROOTS["claims"],
        DEFAULT_ROOTS["durable_evidence"],
    ]
    for key in ("durable_roots", "generated_roots", "host_local_roots"):
        candidates.extend(profile.evidence.get(key, ()))
    return tuple(dict.fromkeys(item for item in candidates if item))


def table_version(payload: dict[str, Any]) -> int:
    meta = payload.get("meta")
    if not isinstance(meta, dict):
        return 1
    try:
        return int(meta.get("version") or 1)
    except (TypeError, ValueError):
        return 1
