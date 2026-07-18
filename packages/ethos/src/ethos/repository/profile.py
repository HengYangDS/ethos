from __future__ import annotations

import subprocess
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


@dataclass(frozen=True, slots=True)
class RepositoryProfile:
    root: Path
    exists: bool
    valid: bool
    source: str
    identity: dict[str, str]
    roots: dict[str, str]
    evidence: dict[str, tuple[str, ...]]
    previous_projection: dict[str, str]
    tables: dict[str, dict[str, Any]]


def load_repository_profile(root: Path, *, tree_ref: str | None = None) -> RepositoryProfile:
    repo = root.resolve()
    exists, text = _profile_text(repo, tree_ref)
    roots = dict(DEFAULT_ROOTS)
    identity: dict[str, str] = {}
    evidence: dict[str, tuple[str, ...]] = {}
    previous_projection: dict[str, str] = {}
    tables: dict[str, dict[str, Any]] = {}
    if not exists:
        return RepositoryProfile(
            root=repo,
            exists=False,
            valid=True,
            source="",
            identity=identity,
            roots=roots,
            evidence=evidence,
            previous_projection=previous_projection,
            tables=tables,
        )
    try:
        payload = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return RepositoryProfile(
            root=repo,
            exists=True,
            valid=False,
            source=".ethos/profile.toml",
            identity=identity,
            roots=roots,
            evidence=evidence,
            previous_projection=previous_projection,
            tables=tables,
        )
    identity = {
        str(key): str(value)
        for key, value in payload.items()
        if key in {"profile_id", "profile_version", "ethos_contract_version"}
        and isinstance(value, (str, int))
    }
    tables = {str(key): value for key, value in payload.items() if isinstance(value, dict)}
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
        identity=identity,
        roots=roots,
        evidence=evidence,
        previous_projection=previous_projection,
        tables=tables,
    )


def _profile_text(repo: Path, tree_ref: str | None) -> tuple[bool, str]:
    if (
        tree_ref
        and subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--verify", f"{tree_ref}^{{commit}}"],
            capture_output=True,
            check=False,
            text=True,
        ).returncode
        == 0
    ):
        result = subprocess.run(
            ["git", "-C", str(repo), "show", f"{tree_ref}:.ethos/profile.toml"],
            capture_output=True,
            check=False,
            text=True,
        )
        return result.returncode == 0, result.stdout
    try:
        return True, (repo / ".ethos" / "profile.toml").read_text(encoding="utf-8")
    except OSError:
        return False, ""


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


def profile_table(root: Path, key: str) -> dict[str, Any]:
    profile = load_repository_profile(root)
    return dict(profile.tables.get(key, {}))


def independent_verification_policy_table(root: Path, action: str = "") -> dict[str, str]:
    """Read a provider-neutral independent-verification policy.

    Absence is intentionally `disabled` so no adopter needs this workstation's
    optional provider.  Per-action configuration is limited to policy mode;
    provider accounts, anchors, keys, and host paths remain outside the repo.
    """
    table = profile_table(root, "independent_verification")
    selected: object = table.get("mode", "disabled")
    actions = table.get("actions")
    if action and isinstance(actions, dict) and isinstance(actions.get(action), dict):
        selected = actions[action].get("mode", selected)
    mode = str(selected)
    return {"mode": mode if mode in {"disabled", "optional", "required"} else "disabled"}


def table_version(payload: dict[str, Any]) -> int:
    meta = payload.get("meta")
    if not isinstance(meta, dict):
        return 1
    try:
        return int(meta.get("version") or 1)
    except (TypeError, ValueError):
        return 1
