from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

PRODUCT_SURFACES = (
    "AGENTS.md",
    "CHANGELOG.md",
    "README.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "package.json",
    "pyproject.toml",
    ".config",
    ".github",
    ".gitlab",
    "packages",
    "distributions",
    ".ethos",
    ".agents/skills",
    "docs/README.md",
    "docs/_meta",
    "docs/architecture",
    "docs/concepts",
    "docs/evidence",
    "docs/governance",
    "docs/reference",
    "docs/decisions/accepted",
    "docs/plans",
    "docs/start",
    "evolution",
    "openspec/specs",
    "rules",
    "system",
    "tests/architecture",
    "tools/ci/scripts",
)
HISTORICAL_SURFACE_PREFIXES = (
    "evidence/",
    "openspec/changes/archive/",
    "docs/history/",
    "docs/decisions/superseded/",
)
SKIPPED_PRODUCT_DIR_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "node_modules",
}
TEXT_SUFFIXES = {".md", ".toml", ".yaml", ".yml", ".json", ".py", ".sh", ".txt"}
PERSONAL_PATTERNS = (
    # Product surfaces may use placeholders, reserved example domains, or
    # organization/team identities, but must not bake a real private mailbox
    # or person-address pair into defaults, docs, tests, or release assets.
    re.compile(
        r"\b[A-Z][a-z]+(?:[ ._-][A-Z][A-Za-z]+)+\s*<[^>]+@(?!example\.(?:com|invalid|test)\b)[^>]+>"
    ),
    re.compile(
        r"\b[a-z][a-z0-9._%+-]+@(?!example\.(?:com|invalid|test)\b)[a-z0-9.-]+\.[a-z]{2,}\b",
        re.IGNORECASE,
    ),
)
_MAC_HOME_PREFIX = "/" + "Users" + "/"
_HOME_PROJECT_PREFIX = "~" + "/" + "projects"
LOCAL_PATH_PATTERNS = (
    re.compile(rf"{re.escape(_MAC_HOME_PREFIX)}[^\s`'\")\]]+"),
    re.compile(rf"{re.escape(_HOME_PROJECT_PREFIX)}/[^\s`'\")\]]+"),
)
PRIVATE_INFRA_PATTERNS = (
    re.compile(
        r"\bhttps?://(?:localhost|127\.0\.0\.1|10(?:\.\d{1,3}){3}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2}|192\.168(?:\.\d{1,3}){2})(?::\d+)?[^\s`'\")\]]*",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bssh://git@(?:localhost|127\.0\.0\.1|10(?:\.\d{1,3}){3}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2}|192\.168(?:\.\d{1,3}){2})(?::\d+)?[^\s`'\")\]]*",
        re.IGNORECASE,
    ),
)
ADOPTER_LITERAL_PATTERNS = (
    re.compile(
        r"\b(?:adopters|profiles)/(?!(?:<adopter-id>|sample-adopter|reference-adopter)\b)"
        r"[a-z][a-z0-9_-]*(?:/|\b)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bevidence/parity/(?!generic-shadow\.json|<adopter-id>-shadow\.json)"
        r"[a-z][a-z0-9_-]*-shadow\.json\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"--adopter\s+(?!(?:<adopter-id>|generic|sample-adopter|reference-adopter)\b)"
        r"[a-z][a-z0-9_-]*\b",
        re.IGNORECASE,
    ),
)
_CURRENT_TOKEN = "cur" + "rent"
_DEFERRED_TOKEN = "fu" + "ture"
_CHAT_TOKEN = "cha" + "t"
_INSTRUCTION_TOKEN = "instru" + "ction"
_MIGRATION_TOKEN = "migra" + "tion"
_SESSION_TOKEN = "sess" + "ion"
PHASE_PATTERNS = (
    re.compile(rf"\b{_CURRENT_TOKEN}/{_DEFERRED_TOKEN}\b", re.IGNORECASE),
    re.compile(rf"\b{_DEFERRED_TOKEN}/{_CURRENT_TOKEN}\b", re.IGNORECASE),
)
SESSION_SURFACE_PATTERNS = (
    re.compile(
        rf"\b(?:{_CURRENT_TOKEN}\s+)?{_CHAT_TOKEN} {_INSTRUCTION_TOKEN}\b"
        rf"|\b{_CURRENT_TOKEN} {_MIGRATION_TOKEN} {_INSTRUCTION_TOKEN}\b"
        rf"|\b{_CHAT_TOKEN} {_SESSION_TOKEN}\b",
        re.IGNORECASE,
    ),
)
PACKAGE_METADATA_FILES = (
    "package.json",
    "distributions/npm/package.json",
    "pyproject.toml",
    "packages/ethos/pyproject.toml",
    "packages/ethos-core/pyproject.toml",
)
GENERIC_PLACEHOLDERS = {"", "<your-name-or-team>", "<your-approved-email>"}
ALLOWED_IDENTITY_ROLES = {"maintainer", "reviewer", "contributor", "team", "bot", "service"}


@dataclass(frozen=True)
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
        for key in ("authors", "maintainers")
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


def product_boundary_report(root: Path) -> dict[str, object]:
    """Report product-surface leaks of personal, local, adopter, or phase terms."""
    patterns: list[tuple[str, re.Pattern[str]]] = []
    patterns.extend(("personal_identity_literal", pattern) for pattern in PERSONAL_PATTERNS)
    patterns.extend(("local_workstation_path", pattern) for pattern in LOCAL_PATH_PATTERNS)
    patterns.extend(
        ("private_infrastructure_literal", pattern) for pattern in PRIVATE_INFRA_PATTERNS
    )
    patterns.extend(("adopter_specific_literal", pattern) for pattern in ADOPTER_LITERAL_PATTERNS)
    patterns.extend(("generic_current_future_phase", pattern) for pattern in PHASE_PATTERNS)
    patterns.extend(("session_authority_literal", pattern) for pattern in SESSION_SURFACE_PATTERNS)

    findings: list[Finding] = []
    files = product_surface_files(root)
    for path in files:
        rel = path.relative_to(root).as_posix()
        findings.extend(_line_findings(path, rel, patterns))
    findings.extend(_metadata_findings(root))

    by_kind: dict[str, int] = {}
    for finding in findings:
        by_kind[finding.kind] = by_kind.get(finding.kind, 0) + 1
    return {
        "ok": not findings,
        "state": "clean" if not findings else "blocked",
        "summary": {
            "scanned_file_count": len(files),
            "finding_count": len(findings),
            "by_kind": by_kind,
        },
        "findings": [finding.to_dict() for finding in findings],
        "required_gaps": [finding.code() for finding in findings],
        "policy": {
            "product_surfaces": list(PRODUCT_SURFACES),
            "historical_surface_prefixes": list(HISTORICAL_SURFACE_PREFIXES),
            "package_metadata_files": list(PACKAGE_METADATA_FILES),
            "boundary": (
                "historical evidence may name facts; active product surfaces "
                "and release metadata stay neutral"
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
    if identity_mode not in {"allowlist", "presence", "external"}:
        findings.append(Finding(policy_path, 1, "identity_mode_missing", identity_mode))
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
            "allowed_roles": sorted(ALLOWED_IDENTITY_ROLES),
        },
    }
