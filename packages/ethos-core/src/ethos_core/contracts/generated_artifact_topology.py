"""Generated artifact topology contract.

The contract is path-oriented and adopter-neutral: it decides where classes of
runtime state, generated proof output, reports, and curated evidence may live
without encoding one adopter, profile, or repository-specific fixture name.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

GENERATED_SUFFIXES = frozenset(
    {
        ".coverage",
        ".html",
        ".json",
        ".jsonl",
        ".log",
        ".sqlite",
        ".xml",
    }
)
GENERATED_FILENAMES = frozenset(
    {
        ".coverage",
        "coverage.xml",
        "junit.xml",
        "proof.json",
        "report.json",
    }
)
SOURCE_METADATA_FILENAMES = frozenset(
    {
        "package-lock.json",
        "package.json",
        "pyproject.toml",
        "uv.lock",
    }
)
DECLARATIVE_PREFIXES = frozenset({".config/ethos/"})

PRODUCT_ADOPTER_ROOT_PREFIXES = frozenset(
    {
        "adopters/",
        "profiles/",
        "tests/fixtures/adopters/",
    }
)

_ALLOWED_PREFIXES: tuple[tuple[str, str], ...] = (
    (".cache/local-state/", "host-local runtime state, leases, locks, executions, sessions"),
    ("build/ethos/", "machine generated ETHOS proof, logs, reports, artifacts, projections"),
    ("build/evidence/", "machine generated quality and proof evidence artifacts"),
)
_REVIEW_PREFIXES: tuple[tuple[str, str], ...] = (
    ("docs/evidence/", "curated dated reviewable evidence"),
    ("evidence/chronicle/", "curated judged history evidence"),
    ("evidence/parity/", "tracked parity evidence promoted by explicit command"),
    (
        ".config/ci/scripts/",
        "legacy executable runner home; visible debt, not a generic config pattern",
    ),
)
_DENIED_GENERATED_PREFIXES: tuple[tuple[str, str], ...] = (
    (".config/", "generated_artifact_config_drift"),
    ("docs/current/", "generated_artifact_current_docs_drift"),
    ("docs/architecture/", "generated_artifact_current_docs_drift"),
    ("docs/governance/", "generated_artifact_current_docs_drift"),
    ("docs/reference/", "generated_artifact_current_docs_drift"),
    ("packages/", "generated_artifact_source_drift"),
)


def normalize_artifact_path(path: Path | str) -> str:
    """Return a repository-relative POSIX path without current-directory noise."""
    text = Path(path).as_posix()
    while text.startswith("./"):
        text = text[2:]
    return text.rstrip("/")


def _matches_prefix(rel: str, prefix: str) -> bool:
    clean = prefix.rstrip("/")
    return rel == clean or rel.startswith(f"{clean}/")


def generated_artifact_contract() -> dict[str, object]:
    """Return the stable generated artifact topology contract."""
    return {
        "schema_version": 1,
        "declarative_prefixes": [
            {"prefix": prefix.rstrip("/"), "boundary": "declarative config, policy, and adopter interface only"}
            for prefix in sorted(DECLARATIVE_PREFIXES)
        ],
        "allowed_prefixes": [
            {"prefix": prefix.rstrip("/"), "boundary": boundary}
            for prefix, boundary in _ALLOWED_PREFIXES
        ],
        "review_prefixes": [
            {"prefix": prefix.rstrip("/"), "boundary": boundary}
            for prefix, boundary in _REVIEW_PREFIXES
        ],
        "denied_generated_prefixes": [
            {"prefix": prefix.rstrip("/"), "required_gap": gap}
            for prefix, gap in _DENIED_GENERATED_PREFIXES
        ],
        "generated_suffixes": sorted(GENERATED_SUFFIXES),
        "generated_filenames": sorted(GENERATED_FILENAMES),
        "adopter_specific_product_dirs_allowed": False,
        "product_adopter_root_prefixes": sorted(
            prefix.rstrip("/") for prefix in PRODUCT_ADOPTER_ROOT_PREFIXES
        ),
    }


def is_product_adopter_path(path: Path | str) -> bool:
    """Return whether a product-repository path embeds adopter-specific roots."""
    rel = normalize_artifact_path(path)
    return any(_matches_prefix(rel, prefix) for prefix in PRODUCT_ADOPTER_ROOT_PREFIXES)


def is_config_script_path(path: Path | str) -> bool:
    """Return whether a path lives under the legacy executable config script home."""
    return _matches_prefix(normalize_artifact_path(path), ".config/ci/scripts/")


def is_generated_artifact_path(path: Path | str) -> bool:
    """Return whether a path has the shape of generated runtime/proof output."""
    rel = normalize_artifact_path(path)
    name = rel.rsplit("/", maxsplit=1)[-1]
    if name in SOURCE_METADATA_FILENAMES:
        return False
    suffix = Path(name).suffix
    return name in GENERATED_FILENAMES or suffix in GENERATED_SUFFIXES


def path_policy_for(path: Path | str) -> dict[str, Any]:
    """Classify a repository-relative path under the generated topology contract."""
    rel = normalize_artifact_path(path)
    generated = is_generated_artifact_path(rel)
    if is_product_adopter_path(rel):
        return {
            "path": rel,
            "decision": "deny",
            "boundary": "ETHOS product repositories may not own adopter-specific roots",
            "generated": generated,
            "required_gap": f"generated_artifact_adopter_specific_product_root:{rel}",
        }
    for prefix in DECLARATIVE_PREFIXES:
        if _matches_prefix(rel, prefix) and not generated:
            return {
                "path": rel,
                "decision": "review",
                "boundary": "declarative config, policy, and adopter interface only",
                "generated": generated,
                "required_gap": "",
            }
    for prefix, boundary in _ALLOWED_PREFIXES:
        if _matches_prefix(rel, prefix):
            return {
                "path": rel,
                "decision": "allow",
                "boundary": boundary,
                "generated": generated,
                "required_gap": "",
            }
    for prefix, boundary in _REVIEW_PREFIXES:
        if _matches_prefix(rel, prefix):
            review_gap = (
                f"generated_artifact_config_script_home_legacy:{rel}"
                if is_config_script_path(rel)
                else ""
            )
            return {
                "path": rel,
                "decision": "review",
                "boundary": boundary,
                "generated": generated,
                "required_gap": review_gap,
            }
    for prefix, gap in _DENIED_GENERATED_PREFIXES:
        if _matches_prefix(rel, prefix) and generated:
            return {
                "path": rel,
                "decision": "deny",
                "boundary": "generated output may not live in config, current docs, or source",
                "generated": generated,
                "required_gap": f"{gap}:{rel}",
            }
    if generated and "/" not in rel:
        return {
            "path": rel,
            "decision": "deny",
            "boundary": "repo root is not a generated artifact owner",
            "generated": generated,
            "required_gap": f"generated_artifact_repo_root_drift:{rel}",
        }
    return {
        "path": rel,
        "decision": "ignore",
        "boundary": "not a generated artifact topology subject",
        "generated": generated,
        "required_gap": "",
    }
