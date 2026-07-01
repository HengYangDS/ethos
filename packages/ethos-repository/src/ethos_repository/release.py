from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from ethos_contracts.branch_roles import load_branch_role_policy

REQUIRED_RELEASE_FILES = (
    "README.md",
    "LICENSE",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    ".gitlab-ci.yml",
    ".gitlab/merge_request_templates/default.md",
    ".gitlab/issue_templates/task.md",
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


def release_policy_report(root: Path) -> dict[str, Any]:
    config = release_config(root)
    missing_files = [path for path in REQUIRED_RELEASE_FILES if not (root / path).exists()]
    version = version_manifest(root)
    protected_refs = config.get("protected_refs", {})
    branch_policy = load_branch_role_policy(root)
    expected_protected_branches = list(branch_policy.protected_branches)
    gitlab = config.get("gitlab", {})
    attestation = config.get("attestation", {})
    gaps: list[str] = []
    gaps.extend(f"release_file_missing:{path}" for path in missing_files)
    if not version["all_package_versions_match"]:
        gaps.append("package_version_mismatch")
    if protected_refs.get("branches") != expected_protected_branches:
        gaps.append("protected_branches_policy_missing")
    if protected_refs.get("tags") != ["v*"]:
        gaps.append("protected_tags_policy_missing")
    for key, path in gitlab.items():
        if not (root / path).exists():
            gaps.append(f"gitlab_surface_missing:{key}:{path}")
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
        "gitlab": {
            "ci": gitlab.get("ci", ""),
            "merge_request_template": gitlab.get("merge_request_template", ""),
            "issue_template": gitlab.get("issue_template", ""),
        },
        "attestation": {
            "formats": list(attestation.get("formats", [])),
            "signing": attestation.get("signing", ""),
        },
    }
