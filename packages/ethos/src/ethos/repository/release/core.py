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


def _profile(config: dict[str, Any], provider: str) -> dict[str, Any]:
    """Project one declared forge profile without granting it authority."""
    profiles = config.get("provider_profiles", {})
    profile = profiles.get(provider, {}) if isinstance(profiles, dict) else {}
    if not isinstance(profile, dict):
        profile = {}
    if not profile:
        return {
            "provider": "",
            "remote": "",
            "role": "",
            "capabilities": [],
            "surfaces": {},
        }
    return {
        "provider": str(profile.get("provider") or provider),
        "remote": str(profile.get("remote") or ""),
        "role": str(profile.get("role") or ""),
        "capabilities": _string_list(profile.get("capabilities")),
        "surfaces": _surface_table(profile),
    }


def _host_profile(config: dict[str, Any]) -> dict[str, Any]:
    """Keep the GitLab primary profile available to legacy adapter views."""
    profile = _profile(config, "gitlab")
    if profile["provider"]:
        return {
            "provider": str(profile["provider"]),
            "layer": "profile_config",
            "surfaces": dict(profile["surfaces"]),
        }
    legacy = config.get("host_profile", {})
    if isinstance(legacy, dict) and legacy:
        return {
            "provider": str(legacy.get("provider", "")),
            "layer": "profile_config",
            "surfaces": _surface_table(legacy),
        }
    return {"provider": "", "layer": "profile_config", "surfaces": {}}


def publication_topology(config: dict[str, Any]) -> dict[str, Any]:
    """Project local and two complete provider planes from tracked policy."""
    topology = config.get("publication_topology", {})
    topology = topology if isinstance(topology, dict) else {}
    mode = str(topology.get("mode") or "")
    modern = mode == "three_layer_peer_complete"
    gitlab = _profile(config, "gitlab")
    github = _profile(config, "github")
    capabilities = _string_list(topology.get("provider_capabilities"))
    remote_accepted_branches = _string_list(topology.get("remote_accepted_branches"))
    remote_excluded_branches = _string_list(topology.get("remote_excluded_branches"))
    return {
        "mode": mode,
        "local": {
            "role": str(topology.get("local_role") or "verification_and_install"),
            "remote_independent": True,
        },
        "gitlab": {
            "provider": str(gitlab["provider"] or "gitlab"),
            "remote": str(gitlab["remote"] or topology.get("primary_remote") or "origin"),
            "role": str(gitlab["role"] or ("organization_primary_publication" if modern else "")),
            "capabilities": _string_list(gitlab["capabilities"]) or capabilities,
            "surfaces": dict(gitlab["surfaces"]),
        },
        "github": {
            "provider": str(github["provider"] or "github"),
            "remote": str(github["remote"] or topology.get("github_remote") or "github"),
            "role": str(github["role"] or ("independent_complete_repository" if modern else "")),
            "capabilities": _string_list(github["capabilities"]) or capabilities,
            "surfaces": dict(github["surfaces"]),
        },
        "remote_ref_policy": {
            "accepted_branches": remote_accepted_branches,
            "excluded_branches": remote_excluded_branches,
        },
    }


def _publication_topology_gaps(
    root: Path,
    topology: dict[str, Any],
    *,
    branch_policy: Any,
) -> list[str]:
    """Return missing complete-provider surfaces and capability declaration gaps."""
    gaps: list[str] = []
    if topology["mode"] != "three_layer_peer_complete":
        return gaps
    required_capabilities = {"repository", "ci_cd", "update", "distribution"}
    required_surfaces = {"ci", "review_template", "issue_template"}
    remote_ref_policy = topology["remote_ref_policy"]
    expected_accepted_branches = [
        branch_policy.accepted_branch,
        branch_policy.release_branch,
        f"{branch_policy.submit_branch_prefix}*",
    ]
    accepted_branches = _string_list(remote_ref_policy["accepted_branches"])
    excluded_branches = _string_list(remote_ref_policy["excluded_branches"])
    if accepted_branches != expected_accepted_branches:
        gaps.append("remote_accepted_branches_policy_missing")
    if branch_policy.candidate_branch in accepted_branches:
        gaps.append("remote_candidate_branch_accepted")
    if branch_policy.candidate_branch not in excluded_branches:
        gaps.append("remote_candidate_branch_not_excluded")
    for provider_key, incomplete_gap in (
        ("gitlab", "publication_gitlab_capabilities_incomplete"),
        ("github", "publication_github_capabilities_incomplete"),
    ):
        profile = topology[provider_key]
        provider = str(profile["provider"])
        for key, path in profile["surfaces"].items():
            if not (root / path).exists():
                gaps.append(f"host_surface_missing:{provider}:{key}:{path}")
        if not str(profile["provider"]) or not str(profile["remote"]):
            gaps.append(f"publication_{provider_key}_remote_incomplete")
        if not str(profile["role"]):
            gaps.append(f"publication_{provider_key}_role_missing")
        if set(_string_list(profile["capabilities"])) != required_capabilities:
            gaps.append(incomplete_gap)
        for surface in sorted(required_surfaces - set(profile["surfaces"])):
            gaps.append(f"publication_{provider_key}_surface_missing:{surface}")
    return gaps


def remote_ref_policy_report(root: Path) -> dict[str, Any]:
    """Return the configured hosted-ref boundary without observing a remote."""
    policy = load_branch_role_policy(root)
    topology = publication_topology(release_config(root))
    ref_policy = topology["remote_ref_policy"]
    accepted_branches = _string_list(ref_policy["accepted_branches"])
    excluded_branches = _string_list(ref_policy["excluded_branches"])
    expected_accepted_branches = [
        policy.accepted_branch,
        policy.release_branch,
        f"{policy.submit_branch_prefix}*",
    ]
    gaps: list[str] = []
    if topology["mode"] != "three_layer_peer_complete":
        gaps.append("remote_ref_policy_unavailable")
    if accepted_branches != expected_accepted_branches:
        gaps.append("remote_accepted_branches_policy_missing")
    if policy.candidate_branch in accepted_branches:
        gaps.append("remote_candidate_branch_accepted")
    if policy.candidate_branch not in excluded_branches:
        gaps.append("remote_candidate_branch_not_excluded")
    return {
        "ok": not gaps,
        "accepted_branches": accepted_branches,
        "excluded_branches": excluded_branches,
        "candidate_branch": policy.candidate_branch,
        "required_gaps": gaps,
    }


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
    gaps.extend(_publication_topology_gaps(root, topology, branch_policy=branch_policy))
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
