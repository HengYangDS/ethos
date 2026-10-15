"""Classify adverse findings that no official stable upstream release fixes yet."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from packaging.version import InvalidVersion
from packaging.version import Version

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping

    from ethos.repository.policy.quality.dependency_acceptance import AuditSubject

NpmArtifact = tuple[str, str]
_BUNDLE = "/node_modules/"
_ROOT = "node_modules/"


def npm_owner(node: str, packages: Mapping[str, dict]) -> NpmArtifact:
    """Return the locked artifact that ships a node: itself, or the package bundling it."""
    while packages[node].get("inBundle") is True and _BUNDLE in node:
        node = node.rsplit(_BUNDLE, 1)[0]
    name, version = node.rsplit(_ROOT, 1)[-1], packages[node].get("version")
    if not node.startswith(_ROOT) or not name or not isinstance(version, str) or not version:
        message = "npm owning artifact unavailable"
        raise ValueError(message)
    return name, version


def npm_owners(
    subjects: Iterable[AuditSubject], lock_source: bytes
) -> dict[AuditSubject, frozenset[NpmArtifact]]:
    """Bind each exact npm subject to the locked artifacts an upgrade would have to replace."""
    packages = json.loads(lock_source)["packages"]
    return {
        subject: frozenset(npm_owner(node, packages) for node in subject[4]) for subject in subjects
    }


def unfixed_npm_subjects(
    owners: Mapping[AuditSubject, frozenset[NpmArtifact]], latest: Mapping[str, object]
) -> set[AuditSubject]:
    """No stable fix exists while every owning artifact already is its latest stable release."""
    return {
        subject
        for subject, artifacts in owners.items()
        if artifacts and all(latest.get(name) == version for name, version in artifacts)
    }


def python_findings(check: dict) -> tuple[set[AuditSubject], set[AuditSubject]] | None:
    """Return exact Python advisories and the unfixed ones; adverse statuses stay strict."""
    if check["verdict"] == "pass":
        return set(), set()
    raw = json.loads(check["stdout"])
    if check["verdict"] != "block" or raw["adverse_statuses"]:
        return None
    subjects: set[AuditSubject] = set()
    unfixed: set[AuditSubject] = set()
    for finding in raw["vulnerabilities"]:
        dependency, fixes = finding["dependency"], finding["fix_versions"]
        identity = finding["id"], dependency["name"], dependency["version"]
        if not all(isinstance(value, str) and value for value in identity) or not isinstance(
            fixes, list
        ):
            message = "invalid Python advisory identity"
            raise ValueError(message)
        subject = (f"python:{identity[0]}", identity[1], identity[2], "", ())
        subjects.add(subject)
        if not any(_stable_fix(fix, identity[2]) for fix in fixes):
            unfixed.add(subject)
    if not subjects:
        message = "Python advisory roots unavailable"
        raise ValueError(message)
    return subjects, unfixed


def _stable_fix(candidate: object, locked: str) -> bool:
    """Only an official stable release newer than the locked one is a fix; unknown fails closed."""
    try:
        fix, current = Version(str(candidate)), Version(locked)
    except InvalidVersion:
        return True
    return not (fix.is_prerelease or fix.is_devrelease) and fix > current
