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
SOURCE_SCHEMA_SUFFIX = ".schema.json"
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
    ("docs/architecture/", "generated_artifact_docs_truth_drift"),
    ("docs/concepts/", "generated_artifact_docs_truth_drift"),
    ("docs/decisions/", "generated_artifact_docs_truth_drift"),
    ("docs/governance/", "generated_artifact_docs_truth_drift"),
    ("docs/history/", "generated_artifact_docs_truth_drift"),
    ("docs/plans/", "generated_artifact_docs_truth_drift"),
    ("docs/reference/", "generated_artifact_docs_truth_drift"),
    ("docs/start/", "generated_artifact_docs_truth_drift"),
    ("packages/", "generated_artifact_source_drift"),
)


def normalize_artifact_path(path: Path | str) -> str:
    """Return a repository-relative POSIX path without current-directory noise."""
    # Path.as_posix() already collapses "./" segments, so only a trailing slash
    # can remain to strip.
    return Path(path).as_posix().rstrip("/")


def _matches_prefix(rel: str, prefix: str) -> bool:
    clean = prefix.rstrip("/")
    return rel == clean or rel.startswith(f"{clean}/")


def generated_artifact_contract() -> dict[str, object]:
    """Return the stable generated artifact topology contract."""
    declarative_boundary = "declarative config, policy, and adopter interface only"
    return {
        "schema_version": 1,
        "declarative_prefixes": [
            {"prefix": prefix.rstrip("/"), "boundary": declarative_boundary}
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
    if name.endswith(SOURCE_SCHEMA_SUFFIX):
        return False
    suffix = Path(name).suffix
    return name in GENERATED_FILENAMES or suffix in GENERATED_SUFFIXES


def _policy(
    *,
    path: str,
    decision: str,
    boundary: str,
    generated: bool,
    required_gap: str = "",
) -> dict[str, Any]:
    return {
        "path": path,
        "decision": decision,
        "boundary": boundary,
        "generated": generated,
        "required_gap": required_gap,
    }


def _product_adopter_policy(rel: str, *, generated: bool) -> dict[str, Any] | None:
    if not is_product_adopter_path(rel):
        return None
    return _policy(
        path=rel,
        decision="deny",
        boundary="ETHOS product repositories may not own adopter-specific roots",
        generated=generated,
        required_gap=f"generated_artifact_adopter_specific_product_root:{rel}",
    )


def _declarative_policy(rel: str, *, generated: bool) -> dict[str, Any] | None:
    if generated:
        return None
    if not any(_matches_prefix(rel, prefix) for prefix in DECLARATIVE_PREFIXES):
        return None
    return _policy(
        path=rel,
        decision="review",
        boundary="declarative config, policy, and adopter interface only",
        generated=generated,
    )


def _allowed_policy(rel: str, *, generated: bool) -> dict[str, Any] | None:
    for prefix, boundary in _ALLOWED_PREFIXES:
        if _matches_prefix(rel, prefix):
            return _policy(
                path=rel,
                decision="allow",
                boundary=boundary,
                generated=generated,
            )
    return None


def _review_policy(rel: str, *, generated: bool) -> dict[str, Any] | None:
    for prefix, boundary in _REVIEW_PREFIXES:
        if _matches_prefix(rel, prefix):
            review_gap = (
                f"generated_artifact_config_script_home_legacy:{rel}"
                if is_config_script_path(rel)
                else ""
            )
            return _policy(
                path=rel,
                decision="review",
                boundary=boundary,
                generated=generated,
                required_gap=review_gap,
            )
    return None


def _generated_denial_policy(rel: str, *, generated: bool) -> dict[str, Any] | None:
    if not generated:
        return None
    for prefix, gap in _DENIED_GENERATED_PREFIXES:
        if _matches_prefix(rel, prefix):
            return _policy(
                path=rel,
                decision="deny",
                boundary="generated output may not live in config, semantic docs truth, or source",
                generated=generated,
                required_gap=f"{gap}:{rel}",
            )
    if "/" not in rel:
        return _policy(
            path=rel,
            decision="deny",
            boundary="repo root is not a generated artifact owner",
            generated=generated,
            required_gap=f"generated_artifact_repo_root_drift:{rel}",
        )
    return None


def path_policy_for(path: Path | str) -> dict[str, Any]:
    """Classify a repository-relative path under the generated topology contract."""
    rel = normalize_artifact_path(path)
    generated = is_generated_artifact_path(rel)
    for candidate in (
        _product_adopter_policy(rel, generated=generated),
        _declarative_policy(rel, generated=generated),
        _allowed_policy(rel, generated=generated),
        _review_policy(rel, generated=generated),
        _generated_denial_policy(rel, generated=generated),
    ):
        if candidate is not None:
            return candidate
    return _policy(
        path=rel,
        decision="ignore",
        boundary="not a generated artifact topology subject",
        generated=generated,
    )
