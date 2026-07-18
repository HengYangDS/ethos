from __future__ import annotations

import re

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
RELEASE_VISIBLE_HISTORICAL_SURFACE_PREFIXES = HISTORICAL_SURFACE_PREFIXES
SKIPPED_PRODUCT_DIR_PARTS = {
    ".ethos/state",
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
_EXTERNAL_REFERENCE_SLUG = (
    r"(?!ETHOS\b|OpenSpec\b|GitHub\b|GitLab\b|Superpowers\b|Backlog\b|"
    r"reference-adopter\b|sample-adopter\b)"
    r"[a-z][a-z0-9_]*(?:-[a-z0-9_]+)+"
)
_EXTERNAL_REFERENCE_NAME = (
    r"(?!ETHOS\b|OpenSpec\b|GitHub\b|GitLab\b|Superpowers\b|Backlog\b|MCP\b|"
    r"reference-adopter\b|sample-adopter\b|generic\b|reusable\b|external\b|"
    r"private\b|named\b|product\b|repository\b|reference\b|mechanism\b|"
    r"mechanisms\b|tooling\b|provider\b|providers\b|environment\b|task\b|"
    r"release\b|architecture\b|security\b|quality\b|format\b|docs\b|domain\b|"
    r"local\b|hosted\b|agent\b|adopter\b|adopters\b)"
    r"[a-z][a-z0-9_]*(?:-[a-z0-9_]+)*"
)
_PRIVATE_REFERENCE_PATTERN_TEXTS = (
    # Active product surfaces may discuss generic reference adopters, profiles,
    # providers, and mechanism classes. They must not turn a named private
    # repository or personal work history into product roadmap, policy, or
    # authority. These patterns intentionally describe the *shape* of the leak
    # instead of hardcoding any private adopter name into the product.
    rf"\b{_EXTERNAL_REFERENCE_SLUG}\s+reference repository\b",
    rf"\b{_EXTERNAL_REFERENCE_SLUG}\s+"
    rf"(?:quality|module-layout|governance|repository|mechanism|policy)\s+"
    rf"(?:study|corpus|patterns?|comparison|matrix)\b",
    rf"\b(?:compared with|comparison with|borrowed from|adopted from|relative to)"
    rf"\s+`?{_EXTERNAL_REFERENCE_SLUG}`?(?:'s)?\b",
    rf"\b(?:from|toward)\s+`{_EXTERNAL_REFERENCE_SLUG}`(?:'s)?\b",
    rf"\bcurrent\s+{_EXTERNAL_REFERENCE_NAME}\s*(?:[,/]\s*"
    rf"{_EXTERNAL_REFERENCE_NAME}\s*)*(?:,?\s*and\s+ETHOS|\s*/\s*ETHOS)"
    rf"\s+mechanism comparison\b",
    rf"\bwhich\s+{_EXTERNAL_REFERENCE_NAME}(?:\s+and\s+"
    rf"{_EXTERNAL_REFERENCE_NAME})?\s+mechanisms?\s+were\b",
    rf"\|\s*`?{_EXTERNAL_REFERENCE_NAME}`?\s*\|\s*`?"
    rf"{_EXTERNAL_REFERENCE_NAME}\s+reference checkout`?\s*\|",
    rf"\b{_EXTERNAL_REFERENCE_NAME}\s+reference checkout\b.{{0,80}}"
    rf"\b(?:mechanism source|tooling source|reference adopter|reference product)\b",
    rf"\|\s*Mechanism family\s*\|\s*{_EXTERNAL_REFERENCE_NAME}\s+has\s*\|",
)
PRIVATE_REFERENCE_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE) for pattern in _PRIVATE_REFERENCE_PATTERN_TEXTS
)
_PRIVATE_DOMAIN_MARKER_TEXTS = (
    # Product surfaces must not preserve private adopter or domain-project
    # shorthand as durable roadmap/evidence terms. The rule is shape-based:
    # compact domain/tool abbreviations followed by slash-qualified mechanism
    # names are not enterprise-neutral closeout language. Use generic role terms
    # instead.
    r"\b[a-z][a-z0-9]*mgr/[a-z][a-z0-9-]+(?:\s+[a-z][a-z0-9-]+){0,3}"
    r"\s+(?:mechanism|mechanisms|comparison|inputs?)\b",
)
PRIVATE_DOMAIN_MARKER_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE) for pattern in _PRIVATE_DOMAIN_MARKER_TEXTS
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
DISTRIBUTION_MANIFEST_FILES = (
    "package.json",
    "distributions/npm/package.json",
    "packages/ethos/pyproject.toml",
    "packages/ethos-core/pyproject.toml",
)
DISTRIBUTION_ALLOWED_FILE_ENTRIES = {
    "README.md",
    "LICENSE",
    "package.json",
}
DISTRIBUTION_ALLOWED_FILE_PREFIXES = ("bin/",)
DISTRIBUTION_FORBIDDEN_FILE_PREFIXES = (
    ".ethos/",
    ".git",
    "build/",
    "docs/history/",
    "evidence/",
    "openspec/changes/archive/",
    "tests/",
)
GENERIC_PLACEHOLDERS = {"", "<your-name-or-team>", "<your-approved-email>"}
ALLOWED_IDENTITY_ROLES = {"maintainer", "reviewer", "contributor", "team", "bot", "service"}
DISTINCT_IDENTITY_FACTS = (
    "git_author",
    "git_committer",
    "work_lane_actor",
    "reviewer",
    "maintainer",
    "bot",
    "team",
    "adopter_side_owner",
)
