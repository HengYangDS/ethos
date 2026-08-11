from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING
from typing import Any

from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.verdict import close_verdict
from ethos.repository.release.publication import publication_topology

if TYPE_CHECKING:
    from pathlib import Path

REQUIRED_RELEASE_FILES = (
    "README.md",
    "LICENSE",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    ".ethos/release.toml",
)


def _toml(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _optional_toml(path: Path) -> dict[str, Any] | None:
    try:
        return _toml(path)
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return None


def release_config(root: Path) -> dict[str, Any]:
    path = root / ".ethos" / "release.toml"
    if not path.exists():
        return {}
    return _optional_toml(path) or {}


def _runtime_files_identity(root: Path, workspace: dict[str, Any]) -> tuple[str, str] | None:
    tools = workspace.get("tool")
    candidates = (
        [
            (name, declaration)
            for name, declaration in tools.items()
            if isinstance(declaration, dict) and declaration.get("distribution") == "runtime-files"
        ]
        if isinstance(tools, dict)
        else []
    )
    if len(candidates) != 1:
        return None
    name, declaration = candidates[0]
    source = declaration.get("version-source")
    if not isinstance(name, str) or not name or not isinstance(source, str) or not source:
        return None
    version_path = (root / source).resolve()
    if not version_path.is_relative_to(root.resolve()) or not version_path.is_file():
        return None
    try:
        version = version_path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return None
    return (name, version) if version else None


def version_manifest(root: Path) -> dict[str, Any]:
    workspace = _optional_toml(root / "pyproject.toml") or {}
    project = workspace.get("project")
    identity: tuple[str, str] | None = None
    packages: dict[str, str] = {}
    if isinstance(project, dict):
        name, version = project.get("name"), project.get("version")
        if isinstance(name, str) and name and isinstance(version, str) and version:
            identity = (name, version)
            packages[name] = version
    identity = identity or _runtime_files_identity(root, workspace)
    name, version = identity or (root.name, "")
    return {
        "name": name,
        "version": version,
        "tag": f"v{version}" if version else "",
        "packages": packages,
        "all_package_versions_match": True,
        "mismatches": {},
        "required_gaps": [] if identity else ["release_version_manifest_invalid"],
    }


def _host_profile(config: dict[str, Any]) -> dict[str, Any]:
    profile = config.get("host_profile", {})
    if isinstance(profile, dict) and profile:
        surfaces = profile.get("surfaces", {})
        return {
            "provider": str(profile.get("provider", "")),
            "layer": "profile_config",
            "surfaces": {
                str(key): str(value)
                for key, value in (surfaces if isinstance(surfaces, dict) else {}).items()
            },
        }
    return {"provider": "", "layer": "profile_config", "surfaces": {}}


def release_policy_report(root: Path) -> dict[str, Any]:
    config_path = root / ".ethos" / "release.toml"
    config = release_config(root)
    missing_files = [path for path in REQUIRED_RELEASE_FILES if not (root / path).exists()]
    version = version_manifest(root)
    protected_refs = config.get("protected_refs", {})
    branch_policy = load_branch_role_policy(root)
    expected_protected_branches = list(branch_policy.protected_branches)
    host_profile = _host_profile(config)
    publication = publication_topology(root, config)
    attestation = config.get("attestation", {})
    gaps: list[str] = []
    gaps.extend(f"release_file_missing:{path}" for path in missing_files)
    if config_path.exists() and _optional_toml(config_path) is None:
        gaps.append("release_config_invalid:.ethos/release.toml")
    gaps.extend(version["required_gaps"])
    if not version["all_package_versions_match"]:
        gaps.append("package_version_mismatch")
    if protected_refs.get("branches") != expected_protected_branches:
        gaps.append("protected_branches_policy_missing")
    if protected_refs.get("tags") != ["v*"]:
        gaps.append("protected_tags_policy_missing")
    provider = str(host_profile["provider"])
    for key, path in host_profile["surfaces"].items():
        if not (root / path).exists():
            gaps.append(f"host_surface_missing:{provider}:{key}:{path}")
    if attestation.get("formats") != ["spdx-2.3-json"]:
        gaps.append("attestation_formats_incomplete")
    publication_gaps = publication.get("required_gaps", [])
    if isinstance(publication_gaps, list):
        gaps.extend(str(gap) for gap in publication_gaps)
    return {
        "verdict": close_verdict("pass", required_gaps=tuple(gaps)),
        "required_gaps": gaps,
        "version": version,
        "required_files": list(REQUIRED_RELEASE_FILES),
        "protected_refs": {
            "branches": list(protected_refs.get("branches", [])),
            "tags": list(protected_refs.get("tags", [])),
        },
        "host_profile": host_profile,
        "publication_topology": publication,
        "attestation": {
            "formats": list(attestation.get("formats", [])),
            "signing": attestation.get("signing", ""),
        },
    }
