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
GENERATED_FILENAME_PREFIXES = frozenset({".coverage."})
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
    (".ethos/state/", "native ETHOS local runtime state, leases, locks, executions, sessions"),
    ("build/runtime/tool-cache/", "ignored tool runtime caches keyed by tool name"),
    ("build/runtime/work/", "ignored provider emulator and scratch working state"),
    ("build/ethos/", "machine generated ETHOS proof, logs, reports, artifacts, projections"),
    ("build/evidence/", "machine generated quality and proof evidence artifacts"),
    ("build/artifacts/", "ignored local build and package artifacts"),
)
_REVIEW_PREFIXES: tuple[tuple[str, str], ...] = (
    ("docs/evidence/", "curated dated reviewable evidence"),
    ("evidence/chronicle/", "curated judged history evidence"),
    ("evidence/parity/", "tracked parity evidence promoted by explicit command"),
    ("tools/ci/scripts/", "repository-owned reusable runner scripts"),
)
_DENIED_PREFIXES: tuple[tuple[str, str], ...] = (
    (".config/ci/scripts/", "runner scripts belong under tools/ci/scripts"),
)
_DENIED_ROOT_CACHE_PREFIXES: tuple[tuple[str, str], ...] = (
    (
        ".import_linter_cache/",
        "import-linter cache belongs under build/runtime/tool-cache/import-linter",
    ),
    (
        ".import-linter-cache/",
        "import-linter cache belongs under build/runtime/tool-cache/import-linter",
    ),
    (".pytest_cache/", "pytest cache belongs under build/runtime/tool-cache/pytest"),
    (".ruff_cache/", "Ruff cache belongs under build/runtime/tool-cache/ruff"),
    (".mypy_cache/", "mypy cache belongs under build/runtime/tool-cache/mypy"),
    (".tox/", "tox runtime state belongs under build/runtime/tool-cache/tox"),
    (".nox/", "nox runtime state belongs under build/runtime/tool-cache/nox"),
    (".uv-cache/", "uv cache belongs under build/runtime/tool-cache/uv"),
)
_DENIED_LEGACY_GENERATED_PREFIXES: tuple[tuple[str, str], ...] = (
    ("build/cache/", "legacy cache bucket is not semantic; use build/runtime/tool-cache/<tool>"),
    (
        "build/runtime/gitlab-ci-local/",
        "provider work state belongs under build/runtime/work/gitlab-ci-local",
    ),
    ("dist/", "package artifacts belong under build/artifacts/python"),
)
_DENIED_GENERATED_PREFIXES: tuple[tuple[str, str], ...] = (
    (".config/", "generated_artifact_config_drift"),
    ("docs/", "generated_artifact_governed_docs_drift"),
    ("packages/", "generated_artifact_source_drift"),
)
_LIFECYCLE_CLASSES: tuple[dict[str, Any], ...] = (
    {
        "id": "runtime_cache",
        "homes": (
            ".cache/local-state",
            ".ethos/state",
            "build/runtime/tool-cache",
            "build/runtime/work",
        ),
        "tracked": False,
        "promotion_allowed": False,
        "cleanup": "disposable host-local state; delete or recreate from source commands",
    },
    {
        "id": "machine_evidence",
        "homes": ("build/evidence", "build/ethos"),
        "tracked": False,
        "promotion_allowed": True,
        "cleanup": "regenerate from a HEAD-bound command; promote only by review or command",
    },
    {
        "id": "local_artifact",
        "homes": ("build/artifacts",),
        "tracked": False,
        "promotion_allowed": False,
        "cleanup": "rebuild from package metadata or release commands",
    },
    {
        "id": "curated_evidence",
        "homes": ("docs/evidence", "evidence/chronicle", "evidence/parity"),
        "tracked": True,
        "promotion_allowed": False,
        "cleanup": "retire or supersede by tracked review, not by cache cleanup",
    },
)


def normalize_artifact_path(path: Path | str) -> str:
    """Return a repository-relative POSIX path without current-directory noise."""
    # Path.as_posix() already collapses "./" segments, so only a trailing slash
    # can remain to strip.
    return Path(path).as_posix().rstrip("/")


def _matches_prefix(rel: str, prefix: str) -> bool:
    clean = prefix.rstrip("/")
    return rel == clean or rel.startswith(f"{clean}/")


def generated_artifact_contract() -> dict[str, Any]:
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
        "denied_prefixes": [
            {"prefix": prefix.rstrip("/"), "required_gap": gap} for prefix, gap in _DENIED_PREFIXES
        ],
        "denied_root_cache_prefixes": [
            {"prefix": prefix.rstrip("/"), "required_gap": gap}
            for prefix, gap in _DENIED_ROOT_CACHE_PREFIXES
        ],
        "denied_legacy_generated_prefixes": [
            {"prefix": prefix.rstrip("/"), "required_gap": gap}
            for prefix, gap in _DENIED_LEGACY_GENERATED_PREFIXES
        ],
        "denied_generated_prefixes": [
            {"prefix": prefix.rstrip("/"), "required_gap": gap}
            for prefix, gap in _DENIED_GENERATED_PREFIXES
        ],
        "generated_suffixes": sorted(GENERATED_SUFFIXES),
        "generated_filenames": sorted(GENERATED_FILENAMES),
        "generated_filename_prefixes": sorted(GENERATED_FILENAME_PREFIXES),
        "lifecycle_classes": [
            {**item, "homes": list(item["homes"])} for item in _LIFECYCLE_CLASSES
        ],
        "adopter_specific_product_dirs_allowed": False,
        "product_adopter_root_prefixes": sorted(
            prefix.rstrip("/") for prefix in PRODUCT_ADOPTER_ROOT_PREFIXES
        ),
    }


def is_product_adopter_path(path: Path | str) -> bool:
    """Return whether a product-repository path embeds adopter-specific roots."""
    rel = normalize_artifact_path(path)
    return any(_matches_prefix(rel, prefix) for prefix in PRODUCT_ADOPTER_ROOT_PREFIXES)


def is_runner_script_path(path: Path | str) -> bool:
    """Return whether a path lives under the repository-owned runner script home."""
    return _matches_prefix(normalize_artifact_path(path), "tools/ci/scripts/")


def is_retired_config_script_path(path: Path | str) -> bool:
    """Return whether a path revives the retired executable config script home."""
    return _matches_prefix(normalize_artifact_path(path), ".config/ci/scripts/")


def is_denied_root_cache_path(path: Path | str) -> bool:
    """Return whether a path revives a root-level tool cache home."""
    rel = normalize_artifact_path(path)
    return any(_matches_prefix(rel, prefix) for prefix, _boundary in _DENIED_ROOT_CACHE_PREFIXES)


def is_generated_artifact_path(path: Path | str) -> bool:
    """Return whether a path has the shape of generated runtime/proof output."""
    rel = normalize_artifact_path(path)
    name = rel.rsplit("/", maxsplit=1)[-1]
    if name in SOURCE_METADATA_FILENAMES:
        return False
    if name.endswith(SOURCE_SCHEMA_SUFFIX):
        return False
    suffix = Path(name).suffix
    return (
        name in GENERATED_FILENAMES
        or suffix in GENERATED_SUFFIXES
        or any(name.startswith(prefix) for prefix in GENERATED_FILENAME_PREFIXES)
    )


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


def _retired_path_policy(rel: str, *, generated: bool) -> dict[str, Any] | None:
    for prefix, boundary in _DENIED_PREFIXES:
        if _matches_prefix(rel, prefix):
            return _policy(
                path=rel,
                decision="deny",
                boundary=boundary,
                generated=generated,
                required_gap=f"retired_config_script_home:{rel}",
            )
    return None


def _denied_root_cache_policy(rel: str, *, generated: bool) -> dict[str, Any] | None:
    for prefix, boundary in _DENIED_ROOT_CACHE_PREFIXES:
        if _matches_prefix(rel, prefix):
            return _policy(
                path=rel,
                decision="deny",
                boundary=boundary,
                generated=generated,
                required_gap=f"generated_artifact_root_cache_drift:{rel}",
            )
    return None


def _legacy_generated_policy(rel: str, *, generated: bool) -> dict[str, Any] | None:
    if _matches_prefix(rel, ".cache/") and not _matches_prefix(rel, ".cache/local-state/"):
        return _policy(
            path=rel,
            decision="deny",
            boundary=".cache is reserved for semantic local-state, not flat cache buckets",
            generated=generated,
            required_gap=f"generated_artifact_cache_flat_drift:{rel}",
        )
    for prefix, boundary in _DENIED_LEGACY_GENERATED_PREFIXES:
        if _matches_prefix(rel, prefix):
            return _policy(
                path=rel,
                decision="deny",
                boundary=boundary,
                generated=generated,
                required_gap=f"generated_artifact_legacy_generated_home:{rel}",
            )
    if (
        rel != "build/runtime"
        and _matches_prefix(rel, "build/runtime/")
        and not (
            _matches_prefix(rel, "build/runtime/tool-cache/")
            or _matches_prefix(rel, "build/runtime/work/")
        )
    ):
        return _policy(
            path=rel,
            decision="deny",
            boundary=(
                "build/runtime must be organized by semantic runtime subroot: tool-cache or work"
            ),
            generated=generated,
            required_gap=f"generated_artifact_runtime_flat_drift:{rel}",
        )
    return None


def _review_policy(rel: str, *, generated: bool) -> dict[str, Any] | None:
    for prefix, boundary in _REVIEW_PREFIXES:
        if _matches_prefix(rel, prefix):
            return _policy(
                path=rel,
                decision="review",
                boundary=boundary,
                generated=generated,
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
        _retired_path_policy(rel, generated=generated),
        _denied_root_cache_policy(rel, generated=generated),
        _legacy_generated_policy(rel, generated=generated),
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
