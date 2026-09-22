"""Compile release declarations and separate generic roles from product conformance."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING
from typing import Any

from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.verdict import close_verdict
from ethos.repository.release.identity import product_version
from ethos.repository.release.identity import projected_package_versions
from ethos.repository.release.publication import publication_topology

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.branch.roles import BranchRolePolicy

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
    """Read optional release policy without treating invalid input as absence."""
    gap = "release_config_invalid:.ethos/release.toml"
    path = root / ".ethos" / "release.toml"
    try:
        source = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        if not path.is_symlink():
            return {}
        raise ValueError(gap) from None
    except (OSError, UnicodeError) as error:
        raise ValueError(gap) from error
    return release_config_from_text(source)


def release_config_from_text(source: str) -> dict[str, Any]:
    """Compile the same release declaration from checkout or exact Git bytes."""
    gap = "release_config_invalid:.ethos/release.toml"
    try:
        config = tomllib.loads(source)
    except tomllib.TOMLDecodeError as error:
        raise ValueError(gap) from error
    protected = config.get("protected_refs", {})
    if not isinstance(protected, dict) or set(protected) - {"branches", "tags"}:
        raise ValueError(gap)
    for entries in protected.values():
        if (
            not isinstance(entries, list)
            or any(
                not isinstance(entry, str) or not entry or entry != entry.strip()
                for entry in entries
            )
            or len(entries) != len(set(entries))
        ):
            raise ValueError(gap)
    return config


def release_role_policy_gaps(config: dict[str, Any], policy: BranchRolePolicy) -> list[str]:
    """Compare declared membership with effective roles without product defaults."""
    protected = config.get("protected_refs", {})
    if "branches" in protected and set(protected["branches"]) != set(policy.protected_branches):
        return ["protected_branches_policy_missing"]
    return []


def release_role_policy_report(root: Path) -> dict[str, Any]:
    """Observe common release obligations independently of product packaging."""
    config: dict[str, Any] = {}
    protected_refs: dict[str, Any] = {}
    try:
        config = release_config(root)
        policy = load_branch_role_policy(root)
        gaps = release_role_policy_gaps(config, policy)
        protected_refs = {
            "branches": list(policy.protected_branches),
            "tags": list(config.get("protected_refs", {}).get("tags", [])),
        }
    except (OSError, UnicodeError, ValueError) as error:
        gaps = [str(error)]
    return {
        "verdict": close_verdict("pass", required_gaps=tuple(gaps)),
        "required_gaps": gaps,
        "declaration": config,
        "protected_refs": protected_refs,
        "next_action": (
            f"repair {root / '.ethos/release.toml'} against configured branch roles" if gaps else ""
        ),
    }


def version_manifest(root: Path) -> dict[str, Any]:
    workspace = _optional_toml(root / "pyproject.toml") or {}
    project = workspace.get("project")
    name = str(project.get("name") or "") if isinstance(project, dict) else ""
    dynamic = project.get("dynamic", []) if isinstance(project, dict) else []
    valid_project = (
        isinstance(project, dict)
        and bool(name)
        and project.get("version") is None
        and isinstance(dynamic, list)
        and "version" in dynamic
    )
    gaps = [] if valid_project else ["release_version_manifest_invalid"]
    version = ""
    if valid_project:
        try:
            version = product_version(root)
        except ValueError as error:
            gaps.append(str(error))
        launcher_paths = (
            root / "distributions/npm/package.json",
            root / "package-lock.json",
            root / "package.json",
        )
        if any(path.exists() for path in launcher_paths):
            try:
                projected_package_versions(root)
            except ValueError as error:
                gaps.append(str(error))
    packages = {name: version} if name and version else {}
    return {
        "name": name or root.name,
        "version": version,
        "tag": f"v{version}" if version else "",
        "packages": packages,
        "all_package_versions_match": not gaps,
        "mismatches": {},
        "required_gaps": list(dict.fromkeys(gaps)),
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
    role_report = release_role_policy_report(root)
    config = role_report["declaration"]
    missing_files = [path for path in REQUIRED_RELEASE_FILES if not (root / path).exists()]
    version = version_manifest(root)
    protected_refs = role_report["protected_refs"]
    host_profile = _host_profile(config)
    publication = publication_topology(root, config)
    attestation = config.get("attestation", {})
    gaps: list[str] = list(role_report["required_gaps"])
    gaps.extend(f"release_file_missing:{path}" for path in missing_files)
    gaps.extend(version["required_gaps"])
    if not version["all_package_versions_match"]:
        gaps.append("package_version_mismatch")
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
        "protected_refs": protected_refs,
        "host_profile": host_profile,
        "publication_topology": publication,
        "attestation": {
            "formats": list(attestation.get("formats", [])),
            "signing": attestation.get("signing", ""),
        },
    }
