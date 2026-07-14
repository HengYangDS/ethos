from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING
from typing import Any

from ethos_core.contracts.branch.roles import load_branch_role_policy

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


def release_config(root: Path) -> dict[str, Any]:
    path = root / ".ethos" / "release.toml"
    if not path.exists():
        return {}
    return _toml(path)


def version_manifest(root: Path) -> dict[str, Any]:
    workspace = _toml(root / "pyproject.toml")["project"]
    version = str(workspace["version"])
    packages: dict[str, str] = {}
    for pyproject in sorted((root / "packages").glob("*/pyproject.toml")):
        project = _toml(pyproject)["project"]
        packages[str(project["name"])] = str(project["version"])
    mismatches = {
        name: package_version
        for name, package_version in packages.items()
        if package_version != version
    }
    return {
        "name": str(workspace["name"]),
        "version": version,
        "tag": f"v{version}",
        "packages": packages,
        "all_package_versions_match": not mismatches,
        "mismatches": mismatches,
    }


def _string_list(value: object) -> list[str]:
    """Return a stable list of string values from a TOML array-shaped field."""
    return [str(item) for item in value] if isinstance(value, list) else []


def _surface_table(profile: object) -> dict[str, str]:
    """Normalize a provider surface mapping without granting it authority."""
    if not isinstance(profile, dict):
        return {}
    surfaces = profile.get("surfaces", {})
    return {
        str(key): str(value)
        for key, value in (surfaces.items() if isinstance(surfaces, dict) else ())
    }


def _host_profile(config: dict[str, Any]) -> dict[str, Any]:
    profile = config.get("host_profile", {})
    if isinstance(profile, dict) and profile:
        return {
            "provider": str(profile.get("provider", "")),
            "layer": "profile_config",
            "surfaces": _surface_table(profile),
        }
    return {"provider": "", "layer": "profile_config", "surfaces": {}}


def publication_topology(config: dict[str, Any]) -> dict[str, Any]:
    """Project local, primary, and mirror release roles from tracked policy.

    This is a policy declaration, not proof of any remote's reachability or a
    successful publication.  The local layer remains remote-independent.
    """
    topology = config.get("publication_topology", {})
    mirror = config.get("mirror_profile", {})
    if not isinstance(topology, dict):
        topology = {}
    if not isinstance(mirror, dict):
        mirror = {}
    return {
        "mode": str(topology.get("mode") or ""),
        "local": {
            "role": str(topology.get("local_role") or "verification_and_install"),
            "remote_independent": True,
        },
        "primary": {
            "provider": str(topology.get("primary_provider") or ""),
            "remote": str(topology.get("primary_remote") or "origin"),
            "role": "organization_primary_publication",
        },
        "mirror": {
            "provider": str(mirror.get("provider") or topology.get("mirror_provider") or ""),
            "remote": str(mirror.get("remote") or topology.get("mirror_remote") or ""),
            "role": str(mirror.get("role") or topology.get("mirror_role") or ""),
            "surfaces": _surface_table(mirror),
            "may_substitute_for": _string_list(topology.get("mirror_may_substitute_for")),
            "may_not_substitute_for": _string_list(topology.get("mirror_may_not_substitute_for")),
        },
    }


def _publication_topology_gaps(root: Path, topology: dict[str, Any]) -> list[str]:
    """Return missing mirror surfaces and required topology declaration gaps."""
    gaps: list[str] = []
    mirror = topology["mirror"]
    mirror_provider = str(mirror["provider"])
    for key, path in mirror["surfaces"].items():
        if not (root / path).exists():
            gaps.append(f"host_surface_missing:{mirror_provider}:{key}:{path}")
    if topology["mode"] == "three_layer_dual_remote":
        primary = topology["primary"]
        if not str(primary["provider"]) or not str(primary["remote"]):
            gaps.append("publication_primary_remote_incomplete")
        if not mirror_provider or not str(mirror["remote"]):
            gaps.append("publication_mirror_remote_incomplete")
        if not str(mirror["role"]):
            gaps.append("publication_mirror_role_missing")
    return gaps


def release_policy_report(root: Path) -> dict[str, Any]:
    config = release_config(root)
    missing_files = [path for path in REQUIRED_RELEASE_FILES if not (root / path).exists()]
    version = version_manifest(root)
    protected_refs = config.get("protected_refs", {})
    branch_policy = load_branch_role_policy(root)
    expected_protected_branches = list(branch_policy.protected_branches)
    host_profile = _host_profile(config)
    attestation = config.get("attestation", {})
    topology = publication_topology(config)
    gaps: list[str] = []
    gaps.extend(f"release_file_missing:{path}" for path in missing_files)
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
    gaps.extend(_publication_topology_gaps(root, topology))
    if set(attestation.get("formats", [])) < {"in-toto", "slsa", "spdx-lite"}:
        gaps.append("attestation_formats_incomplete")
    return {
        "ok": not gaps,
        "required_gaps": gaps,
        "version": version,
        "required_files": list(REQUIRED_RELEASE_FILES),
        "protected_refs": {
            "branches": list(protected_refs.get("branches", [])),
            "tags": list(protected_refs.get("tags", [])),
        },
        "host_profile": host_profile,
        "publication_topology": topology,
        "attestation": {
            "formats": list(attestation.get("formats", [])),
            "signing": attestation.get("signing", ""),
        },
    }
