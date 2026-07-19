from __future__ import annotations

import os
import tomllib
from typing import TYPE_CHECKING
from typing import Any

from ethos.repository.release.publication import publication_topology
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


def _local_command_gaps(root: Path, publication: dict[str, Any]) -> list[str]:
    local = publication.get("local", {})
    local = local if isinstance(local, dict) else {}
    resolved_root = root.resolve()
    gaps: list[str] = []
    for field in ("verification_command", "installation_command"):
        command = str(local.get(field) or "")
        if not command:
            gaps.append(f"release_local_command_missing:{field}:")
            continue
        command_path = (resolved_root / command).resolve()
        if not command_path.is_relative_to(resolved_root):
            gaps.append(f"release_local_command_path_escape:{field}:{command}")
        elif not command_path.exists():
            gaps.append(f"release_local_command_missing:{field}:{command}")
        elif not command_path.is_file():
            gaps.append(f"release_local_command_not_regular:{field}:{command}")
        elif not os.access(command_path, os.X_OK):
            gaps.append(f"release_local_command_not_executable:{field}:{command}")
    return gaps


def release_policy_report(root: Path) -> dict[str, Any]:
    config = release_config(root)
    missing_files = [path for path in REQUIRED_RELEASE_FILES if not (root / path).exists()]
    version = version_manifest(root)
    protected_refs = config.get("protected_refs", {})
    branch_policy = load_branch_role_policy(root)
    expected_protected_branches = list(branch_policy.protected_branches)
    host_profile = _host_profile(config)
    publication = publication_topology(config)
    attestation = config.get("attestation", {})
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
    if set(attestation.get("formats", [])) < {"in-toto", "slsa", "spdx-lite"}:
        gaps.append("attestation_formats_incomplete")
    publication_gaps = publication.get("required_gaps", [])
    if isinstance(publication_gaps, list):
        gaps.extend(str(gap) for gap in publication_gaps)
    gaps.extend(_local_command_gaps(root, publication))
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
        "publication_topology": publication,
        "attestation": {
            "formats": list(attestation.get("formats", [])),
            "signing": attestation.get("signing", ""),
        },
    }
