from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    import re
    from collections.abc import Iterable
    from pathlib import Path

from ethos.repository.policy.boundary.catalog import ADOPTER_LITERAL_PATTERNS
from ethos.repository.policy.boundary.catalog import ALLOWED_IDENTITY_ROLES
from ethos.repository.policy.boundary.catalog import DISTINCT_IDENTITY_FACTS
from ethos.repository.policy.boundary.catalog import DISTRIBUTION_ALLOWED_FILE_ENTRIES
from ethos.repository.policy.boundary.catalog import DISTRIBUTION_ALLOWED_FILE_PREFIXES
from ethos.repository.policy.boundary.catalog import DISTRIBUTION_FORBIDDEN_FILE_PREFIXES
from ethos.repository.policy.boundary.catalog import DISTRIBUTION_MANIFEST_FILES
from ethos.repository.policy.boundary.catalog import GENERIC_PLACEHOLDERS
from ethos.repository.policy.boundary.catalog import HISTORICAL_SURFACE_PREFIXES
from ethos.repository.policy.boundary.catalog import LOCAL_PATH_PATTERNS
from ethos.repository.policy.boundary.catalog import PACKAGE_METADATA_FILES
from ethos.repository.policy.boundary.catalog import PERSONAL_PATTERNS
from ethos.repository.policy.boundary.catalog import PHASE_PATTERNS
from ethos.repository.policy.boundary.catalog import PRIVATE_DOMAIN_MARKER_PATTERNS
from ethos.repository.policy.boundary.catalog import PRIVATE_INFRA_PATTERNS
from ethos.repository.policy.boundary.catalog import PRIVATE_REFERENCE_PATTERNS
from ethos.repository.policy.boundary.catalog import PRODUCT_SURFACES
from ethos.repository.policy.boundary.catalog import RELEASE_VISIBLE_HISTORICAL_SURFACE_PREFIXES
from ethos.repository.policy.boundary.catalog import SESSION_SURFACE_PATTERNS
from ethos.repository.policy.boundary.catalog import SKIPPED_PRODUCT_DIR_PARTS
from ethos.repository.policy.boundary.catalog import TEXT_SUFFIXES


@dataclass(frozen=True, slots=True)
class Finding:
    path: str
    line: int
    kind: str
    detail: str

    def code(self) -> str:
        return f"{self.kind}:{self.path}:{self.line}"

    def to_dict(self) -> dict[str, object]:
        return {"path": self.path, "line": self.line, "kind": self.kind, "detail": self.detail}


def _is_text_product_file(path: Path, *, root: Path) -> bool:
    rel = path.relative_to(root).as_posix()
    if rel == ".ethos/state" or rel.startswith(".ethos/state/"):
        return False
    if any(rel.startswith(prefix) for prefix in HISTORICAL_SURFACE_PREFIXES):
        return False
    if any(part in SKIPPED_PRODUCT_DIR_PARTS for part in path.relative_to(root).parts):
        return False
    if not (path.is_file() and (path.suffix in TEXT_SUFFIXES or path.name == "LICENSE")):
        return False
    return any(rel == surface or rel.startswith(f"{surface}/") for surface in PRODUCT_SURFACES)


def product_surface_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for surface in PRODUCT_SURFACES:
        base = root / surface
        if base.is_file() and _is_text_product_file(base, root=root):
            files.append(base)
        elif base.is_dir():
            files.extend(path for path in base.rglob("*") if _is_text_product_file(path, root=root))
    return sorted(set(files))


def _is_text_release_visible_historical_file(path: Path, *, root: Path) -> bool:
    rel = path.relative_to(root).as_posix()
    if rel == ".ethos/state" or rel.startswith(".ethos/state/"):
        return False
    if any(part in SKIPPED_PRODUCT_DIR_PARTS for part in path.relative_to(root).parts):
        return False
    if not (path.is_file() and (path.suffix in TEXT_SUFFIXES or path.name == "LICENSE")):
        return False
    return any(rel.startswith(prefix) for prefix in RELEASE_VISIBLE_HISTORICAL_SURFACE_PREFIXES)


def release_visible_historical_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for prefix in RELEASE_VISIBLE_HISTORICAL_SURFACE_PREFIXES:
        base = root / prefix
        if base.is_file() and _is_text_release_visible_historical_file(base, root=root):
            files.append(base)
        elif base.is_dir():
            files.extend(
                path
                for path in base.rglob("*")
                if _is_text_release_visible_historical_file(path, root=root)
            )
    return sorted(set(files))


def _line_findings(
    path: Path, rel: str, patterns: Iterable[tuple[str, re.Pattern[str]]]
) -> list[Finding]:
    findings: list[Finding] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return findings
    for lineno, line in enumerate(text.splitlines(), start=1):
        for kind, pattern in patterns:
            if pattern.search(line):
                findings.append(Finding(rel, lineno, kind, pattern.pattern))
    return findings


def _path_findings(rel: str, patterns: Iterable[tuple[str, re.Pattern[str]]]) -> list[Finding]:
    return [
        Finding(rel, 1, kind, pattern.pattern) for kind, pattern in patterns if pattern.search(rel)
    ]


def _metadata_findings(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for rel in PACKAGE_METADATA_FILES:
        path = root / rel
        if not path.exists():
            continue
        if path.suffix == ".json":
            findings.extend(_json_package_metadata_findings(path, rel))
        else:
            findings.extend(_toml_package_metadata_findings(path, rel))
    return findings


def _json_package_metadata_findings(path: Path, rel: str) -> list[Finding]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, dict):
        return []
    findings = (
        [Finding(rel, 1, "single_author_metadata", "author")] if payload.get("author") else []
    )
    findings.extend(
        Finding(rel, 1, "person_attribution_metadata", key)
        for key in ("authors", "maintainers", "contributors")
        if payload.get(key)
    )
    return findings


def _toml_package_metadata_findings(path: Path, rel: str) -> list[Finding]:
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return []
    project = payload.get("project")
    if not isinstance(project, dict):
        return []
    findings: list[Finding] = []
    if project.get("authors"):
        findings.append(Finding(rel, 1, "person_attribution_metadata", "project.authors"))
    if project.get("maintainers"):
        findings.append(Finding(rel, 1, "person_attribution_metadata", "project.maintainers"))
    return findings


def _normalized_distribution_file_entries(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(entry).removeprefix("./") for entry in raw if isinstance(entry, str)]


def _npm_distribution_manifest_findings(path: Path, rel: str) -> list[Finding]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, dict):
        return []

    findings: list[Finding] = []
    if rel == "package.json" and payload.get("workspaces") and payload.get("private") is not True:
        findings.append(
            Finding(rel, 1, "root_workspace_package_publishable", "private must be true")
        )

    if rel != "distributions/npm/package.json":
        return findings

    files = _normalized_distribution_file_entries(payload.get("files"))
    if not files:
        findings.append(
            Finding(rel, 1, "distribution_files_allowlist_missing", "files must be explicit")
        )
        return findings

    bin_payload = payload.get("bin")
    if not isinstance(bin_payload, dict) or not bin_payload.get("ethos"):
        findings.append(Finding(rel, 1, "distribution_bin_missing", "bin.ethos"))

    for entry in files:
        allowed = entry in DISTRIBUTION_ALLOWED_FILE_ENTRIES or entry.startswith(
            DISTRIBUTION_ALLOWED_FILE_PREFIXES
        )
        forbidden = entry.startswith(DISTRIBUTION_FORBIDDEN_FILE_PREFIXES)
        if forbidden or not allowed:
            findings.append(Finding(rel, 1, "distribution_file_scope_leak", entry))
    return findings


def _distribution_manifest_findings(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for rel in DISTRIBUTION_MANIFEST_FILES:
        path = root / rel
        if path.exists() and path.suffix == ".json":
            findings.extend(_npm_distribution_manifest_findings(path, rel))
    return findings


def product_boundary_report(root: Path) -> dict[str, object]:
    """Report product-surface leaks of personal, local, adopter, or phase terms."""
    patterns: list[tuple[str, re.Pattern[str]]] = []
    patterns.extend(("personal_identity_literal", pattern) for pattern in PERSONAL_PATTERNS)
    patterns.extend(("local_workstation_path", pattern) for pattern in LOCAL_PATH_PATTERNS)
    patterns.extend(
        ("private_infrastructure_literal", pattern) for pattern in PRIVATE_INFRA_PATTERNS
    )
    patterns.extend(("adopter_specific_literal", pattern) for pattern in ADOPTER_LITERAL_PATTERNS)
    patterns.extend(
        ("private_reference_literal", pattern) for pattern in PRIVATE_REFERENCE_PATTERNS
    )
    patterns.extend(
        ("private_domain_marker_literal", pattern) for pattern in PRIVATE_DOMAIN_MARKER_PATTERNS
    )
    patterns.extend(("generic_current_future_phase", pattern) for pattern in PHASE_PATTERNS)
    patterns.extend(("session_authority_literal", pattern) for pattern in SESSION_SURFACE_PATTERNS)
    archival_patterns: list[tuple[str, re.Pattern[str]]] = [
        (f"archival_{kind}", pattern) for kind, pattern in patterns
    ]

    findings: list[Finding] = []
    files = product_surface_files(root)
    for path in files:
        rel = path.relative_to(root).as_posix()
        findings.extend(_line_findings(path, rel, patterns))
    historical_files = release_visible_historical_files(root)
    for path in historical_files:
        rel = path.relative_to(root).as_posix()
        findings.extend(_path_findings(rel, archival_patterns))
        findings.extend(_line_findings(path, rel, archival_patterns))
    findings.extend(_metadata_findings(root))
    findings.extend(_distribution_manifest_findings(root))

    by_kind: dict[str, int] = {}
    for finding in findings:
        by_kind[finding.kind] = by_kind.get(finding.kind, 0) + 1
    return {
        "ok": not findings,
        "state": "clean" if not findings else "blocked",
        "summary": {
            "scanned_file_count": len(files),
            "release_visible_historical_scanned_file_count": len(historical_files),
            "finding_count": len(findings),
            "by_kind": by_kind,
        },
        "findings": [finding.to_dict() for finding in findings],
        "required_gaps": [finding.code() for finding in findings],
        "policy": {
            "product_surfaces": list(PRODUCT_SURFACES),
            "historical_surface_prefixes": list(HISTORICAL_SURFACE_PREFIXES),
            "release_visible_historical_surface_prefixes": list(
                RELEASE_VISIBLE_HISTORICAL_SURFACE_PREFIXES
            ),
            "local_state_surface_prefixes": [".ethos/state/"],
            "package_metadata_files": list(PACKAGE_METADATA_FILES),
            "distribution_manifest_files": list(DISTRIBUTION_MANIFEST_FILES),
            "distribution_boundary": (
                "published package manifests must allowlist only neutral launcher "
                "assets and must not ship historical evidence, adopter-private "
                "records, local state, tests, or person attribution metadata"
            ),
            "private_reference_boundary": (
                "active product surfaces may describe generic reference adopters "
                "and mechanism classes, but must not depend on named private "
                "repositories or personal work history"
            ),
            "release_visible_historical_boundary": (
                "release-visible chronicles, parity evidence, archived changes, "
                "history, and superseded decisions preserve judged provenance "
                "without raw workstation paths, personal attribution, named "
                "private adopters, or private project dependency literals"
            ),
            "boundary": (
                "product surfaces, release-visible historical provenance, "
                "release metadata, and distribution packages stay enterprise-neutral"
            ),
        },
    }


def _identity_entries(raw: dict[str, Any]) -> list[dict[str, str]]:
    entries = raw.get("allowed_identities", [])
    if not isinstance(entries, list):
        return []
    normalized: list[dict[str, str]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        normalized.append(
            {
                "role": str(entry.get("role", "")),
                "name": str(entry.get("name", "")),
                "email": str(entry.get("email", "")),
            }
        )
    return normalized


def load_workspace_commit_policy(root: Path) -> dict[str, Any]:
    path = root / ".ethos" / "workspace.toml"
    if not path.exists():
        return {}
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return {"parse_failed": True}
    raw = payload.get("commit_policy")
    return raw if isinstance(raw, dict) else {}


def _policy_parse_findings(raw: dict[str, Any], policy_path: str) -> list[Finding]:
    if raw.get("parse_failed"):
        return [Finding(policy_path, 1, "commit_policy_toml_invalid", "TOML parse failed")]
    return []


def _policy_shape_findings(
    *, raw: dict[str, Any], entries: list[dict[str, str]], policy_path: str
) -> list[Finding]:
    findings = [
        Finding(policy_path, 1, "single_author_policy", key)
        for key in ("expected_name", "expected_email")
        if raw.get(key)
    ]

    identity_mode = str(raw.get("identity_mode", ""))
    if not identity_mode:
        findings.append(Finding(policy_path, 1, "identity_mode_missing", identity_mode))
    elif identity_mode != "external":
        findings.append(Finding(policy_path, 1, "identity_mode_not_external", identity_mode))
    if not entries:
        findings.append(
            Finding(policy_path, 1, "allowed_identities_missing", "no identities declared")
        )
    return findings


def _role_coverage_findings(
    *, entries: list[dict[str, str]], roles: set[str], policy_path: str
) -> list[Finding]:
    if not entries:
        return []
    findings: list[Finding] = []
    role_text = ",".join(sorted(roles))
    if not roles.intersection({"maintainer", "team"}):
        findings.append(Finding(policy_path, 1, "maintainer_or_team_missing", role_text))
    if not roles.intersection({"bot", "service"}):
        findings.append(Finding(policy_path, 1, "automation_identity_missing", role_text))
    return findings


def _identity_entry_findings(*, entries: list[dict[str, str]], policy_path: str) -> list[Finding]:
    findings: list[Finding] = []
    for idx, entry in enumerate(entries, start=1):
        role = entry["role"]
        name = entry["name"]
        email = entry["email"]
        if role not in ALLOWED_IDENTITY_ROLES:
            findings.append(Finding(policy_path, idx, "identity_role_unknown", role))
        if name in GENERIC_PLACEHOLDERS or email in GENERIC_PLACEHOLDERS:
            findings.append(Finding(policy_path, idx, "identity_placeholder", f"{name} <{email}>"))
        identity = f"{name} <{email}>"
        if any(pattern.search(identity) for pattern in PERSONAL_PATTERNS):
            findings.append(Finding(policy_path, idx, "personal_identity_literal", identity))
    return findings


def contributor_policy_report(root: Path) -> dict[str, object]:
    """Report whether commit identity policy supports organizations, teams, and bots."""
    raw = load_workspace_commit_policy(root)
    policy_path = ".ethos/workspace.toml"
    entries = [] if raw.get("parse_failed") else _identity_entries(raw)
    roles = {entry["role"] for entry in entries}
    identity_mode = str(raw.get("identity_mode", ""))
    findings = [
        *_policy_parse_findings(raw, policy_path),
        *_policy_shape_findings(raw=raw, entries=entries, policy_path=policy_path),
        *_role_coverage_findings(entries=entries, roles=roles, policy_path=policy_path),
        *_identity_entry_findings(entries=entries, policy_path=policy_path),
    ]

    return {
        "ok": not findings,
        "state": "clean" if not findings else "blocked",
        "summary": {
            "identity_mode": identity_mode,
            "identity_count": len(entries),
            "roles": sorted(roles),
            "finding_count": len(findings),
        },
        "allowed_identities": entries,
        "required_gaps": [finding.code() for finding in findings],
        "findings": [finding.to_dict() for finding in findings],
        "policy": {
            "principle": "Git author / committer != Work Lane actor != governance authority",
            "identity_model": "external_role_policy",
            "distinct_identity_facts": list(DISTINCT_IDENTITY_FACTS),
            "allowed_roles": sorted(ALLOWED_IDENTITY_ROLES),
        },
    }
