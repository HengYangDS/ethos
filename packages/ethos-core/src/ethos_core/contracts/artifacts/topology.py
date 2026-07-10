"""Generated artifact topology contract.

The contract is path-oriented and adopter-neutral: it decides where classes of
runtime state, generated proof output, reports, and curated evidence may live
without encoding one adopter, profile, or repository-specific fixture name.
"""

from __future__ import annotations

import tomllib
from importlib import resources
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict

DECLARATION_PATH = Path("system/policies/generated-artifact-topology.toml")
_DECLARATION_RESOURCE = "data/generated_artifact_topology.toml"


class TopologyPrefix(BaseModel):
    """One declared path-prefix rule for generated artifact topology."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    prefix: str
    boundary: str = ""
    required_gap_prefix: str = ""

    def to_contract(self) -> dict[str, str]:
        """Return the stable public contract shape for a prefix rule."""
        payload = {"prefix": self.prefix.rstrip("/")}
        if self.boundary:
            payload["boundary"] = self.boundary
        if self.required_gap_prefix:
            payload["required_gap"] = self.required_gap_prefix
        return payload


class LifecycleClass(BaseModel):
    """Declared generated-artifact lifecycle class."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    homes: tuple[str, ...]
    tracked: bool
    promotion_allowed: bool
    cleanup: str

    def to_contract(self) -> dict[str, Any]:
        """Return the stable public lifecycle contract shape."""
        return {
            "id": self.id,
            "homes": list(self.homes),
            "tracked": self.tracked,
            "promotion_allowed": self.promotion_allowed,
            "cleanup": self.cleanup,
        }


class GeneratedArtifactTopologyDeclaration(BaseModel):
    """Typed declaration for generated artifact topology policy."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    schema_version: int = 1
    source_refs: tuple[str, ...] = ()
    adopter_specific_product_dirs_allowed: bool = False
    declarative_boundary: str
    product_adopter_boundary: str
    product_adopter_required_gap_prefix: str
    cache_flat_boundary: str
    cache_flat_required_gap_prefix: str
    cache_flat_root_prefix: str
    cache_allowed_prefixes: tuple[str, ...]
    runtime_flat_boundary: str
    runtime_flat_required_gap_prefix: str
    runtime_flat_root_prefix: str
    runtime_allowed_prefixes: tuple[str, ...]
    generated_denial_boundary: str
    repo_root_generated_boundary: str
    repo_root_generated_required_gap_prefix: str
    ignore_boundary: str
    source_schema_suffix: str
    generated_suffixes: tuple[str, ...]
    generated_filenames: tuple[str, ...]
    generated_filename_prefixes: tuple[str, ...]
    source_metadata_filenames: tuple[str, ...]
    product_adopter_root_prefixes: tuple[str, ...]
    declarative_prefix: tuple[TopologyPrefix, ...]
    allowed_prefix: tuple[TopologyPrefix, ...]
    review_prefix: tuple[TopologyPrefix, ...]
    denied_prefix: tuple[TopologyPrefix, ...]
    denied_root_cache_prefix: tuple[TopologyPrefix, ...]
    denied_legacy_generated_prefix: tuple[TopologyPrefix, ...]
    denied_generated_prefix: tuple[TopologyPrefix, ...]
    lifecycle_class: tuple[LifecycleClass, ...]

    def to_contract(self) -> dict[str, Any]:
        """Return the stable generated artifact topology contract."""
        return {
            "schema_version": self.schema_version,
            "source_refs": list(self.source_refs),
            "declarative_prefixes": [
                item.to_contract() for item in sorted(self.declarative_prefix, key=_prefix_key)
            ],
            "allowed_prefixes": [item.to_contract() for item in self.allowed_prefix],
            "review_prefixes": [item.to_contract() for item in self.review_prefix],
            "denied_prefixes": [item.to_contract() for item in self.denied_prefix],
            "denied_root_cache_prefixes": [
                item.to_contract() for item in self.denied_root_cache_prefix
            ],
            "denied_legacy_generated_prefixes": [
                item.to_contract() for item in self.denied_legacy_generated_prefix
            ],
            "denied_generated_prefixes": [
                item.to_contract() for item in self.denied_generated_prefix
            ],
            "generated_suffixes": sorted(self.generated_suffixes),
            "generated_filenames": sorted(self.generated_filenames),
            "generated_filename_prefixes": sorted(self.generated_filename_prefixes),
            "lifecycle_classes": [item.to_contract() for item in self.lifecycle_class],
            "adopter_specific_product_dirs_allowed": self.adopter_specific_product_dirs_allowed,
            "product_adopter_root_prefixes": sorted(
                prefix.rstrip("/") for prefix in self.product_adopter_root_prefixes
            ),
        }


def _prefix_key(item: TopologyPrefix) -> str:
    return item.prefix


def _default_declaration_path() -> Path:
    cwd_candidate = Path.cwd() / DECLARATION_PATH
    if cwd_candidate.exists():
        return cwd_candidate
    for parent in Path(__file__).resolve().parents:
        candidate = parent / DECLARATION_PATH
        if candidate.exists():
            return candidate
    return DECLARATION_PATH


def _declaration_text(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return resources.files("ethos_core").joinpath(_DECLARATION_RESOURCE).read_text(encoding="utf-8")


def load_generated_artifact_topology_declaration(
    path: Path | str | None = None,
) -> GeneratedArtifactTopologyDeclaration:
    """Load the generated-artifact topology declaration from TOML."""
    declaration_path = Path(path) if path is not None else _default_declaration_path()
    payload = tomllib.loads(_declaration_text(declaration_path))
    return GeneratedArtifactTopologyDeclaration.model_validate(payload)


def normalize_artifact_path(path: Path | str) -> str:
    """Return a repository-relative POSIX path without current-directory noise."""
    # Path.as_posix() already collapses "./" segments, so only a trailing slash
    # can remain to strip.
    return Path(path).as_posix().rstrip("/")


def _matches_prefix(rel: str, prefix: str) -> bool:
    clean = prefix.rstrip("/")
    return rel == clean or rel.startswith(f"{clean}/")


def generated_artifact_contract(
    declaration: GeneratedArtifactTopologyDeclaration | None = None,
) -> dict[str, Any]:
    """Return the stable generated artifact topology contract."""
    return (declaration or load_generated_artifact_topology_declaration()).to_contract()


def is_product_adopter_path(
    path: Path | str,
    declaration: GeneratedArtifactTopologyDeclaration | None = None,
) -> bool:
    """Return whether a product-repository path embeds adopter-specific roots."""
    rel = normalize_artifact_path(path)
    topology = declaration or load_generated_artifact_topology_declaration()
    return any(_matches_prefix(rel, prefix) for prefix in topology.product_adopter_root_prefixes)


def is_runner_script_path(path: Path | str) -> bool:
    """Return whether a path lives under the repository-owned runner script home."""
    return _matches_prefix(normalize_artifact_path(path), "tools/ci/scripts/")


def is_retired_config_script_path(path: Path | str) -> bool:
    """Return whether a path revives the retired executable config script home."""
    return _matches_prefix(normalize_artifact_path(path), ".config/ci/scripts/")


def is_denied_root_cache_path(
    path: Path | str,
    declaration: GeneratedArtifactTopologyDeclaration | None = None,
) -> bool:
    """Return whether a path revives a root-level tool cache home."""
    rel = normalize_artifact_path(path)
    topology = declaration or load_generated_artifact_topology_declaration()
    return any(_matches_prefix(rel, item.prefix) for item in topology.denied_root_cache_prefix)


def is_generated_artifact_path(
    path: Path | str,
    declaration: GeneratedArtifactTopologyDeclaration | None = None,
) -> bool:
    """Return whether a path has the shape of generated runtime/proof output."""
    rel = normalize_artifact_path(path)
    topology = declaration or load_generated_artifact_topology_declaration()
    name = rel.rsplit("/", maxsplit=1)[-1]
    if name in topology.source_metadata_filenames:
        return False
    if name.endswith(topology.source_schema_suffix):
        return False
    suffix = Path(name).suffix
    return (
        name in topology.generated_filenames
        or suffix in topology.generated_suffixes
        or any(name.startswith(prefix) for prefix in topology.generated_filename_prefixes)
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


def _gap(prefix: str, rel: str) -> str:
    return f"{prefix}:{rel}" if prefix else ""


def _matched_prefix_policy(
    rel: str,
    *,
    generated: bool,
    prefixes: tuple[TopologyPrefix, ...],
    decision: str,
) -> dict[str, Any] | None:
    for item in prefixes:
        if _matches_prefix(rel, item.prefix):
            return _policy(
                path=rel,
                decision=decision,
                boundary=item.boundary,
                generated=generated,
                required_gap=_gap(item.required_gap_prefix, rel),
            )
    return None


def _product_adopter_policy(
    rel: str,
    *,
    generated: bool,
    declaration: GeneratedArtifactTopologyDeclaration,
) -> dict[str, Any] | None:
    if not is_product_adopter_path(rel, declaration):
        return None
    return _policy(
        path=rel,
        decision="deny",
        boundary=declaration.product_adopter_boundary,
        generated=generated,
        required_gap=_gap(declaration.product_adopter_required_gap_prefix, rel),
    )


def _declarative_policy(
    rel: str,
    *,
    generated: bool,
    declaration: GeneratedArtifactTopologyDeclaration,
) -> dict[str, Any] | None:
    if generated:
        return None
    return _matched_prefix_policy(
        rel,
        generated=generated,
        prefixes=declaration.declarative_prefix,
        decision="review",
    )


def _allowed_policy(
    rel: str,
    *,
    generated: bool,
    declaration: GeneratedArtifactTopologyDeclaration,
) -> dict[str, Any] | None:
    return _matched_prefix_policy(
        rel,
        generated=generated,
        prefixes=declaration.allowed_prefix,
        decision="allow",
    )


def _legacy_generated_policy(
    rel: str,
    *,
    generated: bool,
    declaration: GeneratedArtifactTopologyDeclaration,
) -> dict[str, Any] | None:
    if _matches_prefix(rel, declaration.cache_flat_root_prefix) and not any(
        _matches_prefix(rel, prefix) for prefix in declaration.cache_allowed_prefixes
    ):
        return _policy(
            path=rel,
            decision="deny",
            boundary=declaration.cache_flat_boundary,
            generated=generated,
            required_gap=_gap(declaration.cache_flat_required_gap_prefix, rel),
        )
    declared = _matched_prefix_policy(
        rel,
        generated=generated,
        prefixes=declaration.denied_legacy_generated_prefix,
        decision="deny",
    )
    if declared is not None:
        return declared
    if (
        rel != declaration.runtime_flat_root_prefix
        and _matches_prefix(rel, declaration.runtime_flat_root_prefix)
        and not any(_matches_prefix(rel, prefix) for prefix in declaration.runtime_allowed_prefixes)
    ):
        return _policy(
            path=rel,
            decision="deny",
            boundary=declaration.runtime_flat_boundary,
            generated=generated,
            required_gap=_gap(declaration.runtime_flat_required_gap_prefix, rel),
        )
    return None


def _review_policy(
    rel: str,
    *,
    generated: bool,
    declaration: GeneratedArtifactTopologyDeclaration,
) -> dict[str, Any] | None:
    return _matched_prefix_policy(
        rel,
        generated=generated,
        prefixes=declaration.review_prefix,
        decision="review",
    )


def _generated_denial_policy(
    rel: str,
    *,
    generated: bool,
    declaration: GeneratedArtifactTopologyDeclaration,
) -> dict[str, Any] | None:
    if not generated:
        return None
    declared = _matched_prefix_policy(
        rel,
        generated=generated,
        prefixes=declaration.denied_generated_prefix,
        decision="deny",
    )
    if declared is not None:
        declared["boundary"] = declaration.generated_denial_boundary
        return declared
    if "/" not in rel:
        return _policy(
            path=rel,
            decision="deny",
            boundary=declaration.repo_root_generated_boundary,
            generated=generated,
            required_gap=_gap(declaration.repo_root_generated_required_gap_prefix, rel),
        )
    return None


def path_policy_from_declaration(
    path: Path | str,
    declaration: GeneratedArtifactTopologyDeclaration,
) -> dict[str, Any]:
    """Classify a repository-relative path under the generated topology contract."""
    rel = normalize_artifact_path(path)
    generated = is_generated_artifact_path(rel, declaration)
    for candidate in (
        _product_adopter_policy(rel, generated=generated, declaration=declaration),
        _matched_prefix_policy(
            rel,
            generated=generated,
            prefixes=declaration.denied_prefix,
            decision="deny",
        ),
        _matched_prefix_policy(
            rel,
            generated=generated,
            prefixes=declaration.denied_root_cache_prefix,
            decision="deny",
        ),
        _legacy_generated_policy(rel, generated=generated, declaration=declaration),
        _declarative_policy(rel, generated=generated, declaration=declaration),
        _allowed_policy(rel, generated=generated, declaration=declaration),
        _review_policy(rel, generated=generated, declaration=declaration),
        _generated_denial_policy(rel, generated=generated, declaration=declaration),
    ):
        if candidate is not None:
            return candidate
    return _policy(
        path=rel,
        decision="ignore",
        boundary=declaration.ignore_boundary,
        generated=generated,
    )


def path_policy_for(path: Path | str) -> dict[str, Any]:
    """Classify a repository-relative path under the generated topology contract."""
    return path_policy_from_declaration(path, load_generated_artifact_topology_declaration())
