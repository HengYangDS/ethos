"""Generated artifact topology contract.

The contract is path-oriented and adopter-neutral: it decides where classes of
runtime state, generated proof output, reports, and curated evidence may live
without encoding one adopter, profile, or repository-specific fixture name.
"""

import tomllib
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any
from typing import Literal
from typing import Self
from typing import cast

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import model_validator

from ethos.contracts.policy.cel import evaluate_cel_predicate
from ethos.contracts.value import FrozenTuple

_CEL_RULE_IDS = frozenset(
    {
        "product-adopter-root",
        "denied-prefix",
        "denied-root-cache",
        "cache-flat",
        "denied-legacy-generated",
        "runtime-flat",
        "declarative",
        "allowed",
        "review",
        "owned-projection",
        "denied-generated",
        "repo-root-generated",
    }
)


class TopologyPrefix(BaseModel):
    """One declared path-prefix rule for generated artifact topology."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

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

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    id: str
    homes: FrozenTuple[str]
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


class TopologyCelRule(BaseModel):
    """One ordered, restricted CEL predicate for a topology decision."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    id: Literal[
        "product-adopter-root",
        "denied-prefix",
        "denied-root-cache",
        "cache-flat",
        "denied-legacy-generated",
        "runtime-flat",
        "declarative",
        "allowed",
        "review",
        "owned-projection",
        "denied-generated",
        "repo-root-generated",
    ]
    expression: str
    decision: Literal["allow", "review", "deny"]
    boundary: str = ""
    required_gap_prefix: str = ""
    prefix_group: Literal[
        "",
        "declarative_prefix",
        "allowed_prefix",
        "review_prefix",
        "denied_prefix",
        "denied_root_cache_prefix",
        "denied_legacy_generated_prefix",
        "denied_generated_prefix",
    ] = ""


class GeneratedArtifactTopologyDeclaration(BaseModel):
    """Typed declaration for generated artifact topology policy."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    id: str
    source_refs: FrozenTuple[str] = ()
    adopter_specific_product_dirs_allowed: bool = False
    cache_flat_root_prefix: str
    cache_allowed_prefixes: FrozenTuple[str]
    runtime_flat_root_prefix: str
    runtime_allowed_prefixes: FrozenTuple[str]
    ignore_boundary: str
    product_adopter_root_prefixes: FrozenTuple[str]
    declarative_prefix: FrozenTuple[TopologyPrefix]
    allowed_prefix: FrozenTuple[TopologyPrefix]
    review_prefix: FrozenTuple[TopologyPrefix]
    denied_prefix: FrozenTuple[TopologyPrefix]
    denied_root_cache_prefix: FrozenTuple[TopologyPrefix]
    denied_legacy_generated_prefix: FrozenTuple[TopologyPrefix]
    denied_generated_prefix: FrozenTuple[TopologyPrefix]
    lifecycle_class: FrozenTuple[LifecycleClass]
    cel_rule: FrozenTuple[TopologyCelRule]

    @model_validator(mode="after")
    def validate_cel_rules(self) -> Self:
        """Require the complete ordered topology rule set before evaluation."""
        ids = [rule.id for rule in self.cel_rule]
        if len(ids) != len(set(ids)) or set(ids) != _CEL_RULE_IDS:
            msg = "topology CEL rule ids must be unique and complete"
            raise ValueError(msg)
        return self

    def to_contract(self) -> dict[str, Any]:
        """Return the stable generated artifact topology contract."""
        return {
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
            "lifecycle_classes": [item.to_contract() for item in self.lifecycle_class],
            "adopter_specific_product_dirs_allowed": self.adopter_specific_product_dirs_allowed,
            "product_adopter_root_prefixes": sorted(
                prefix.rstrip("/") for prefix in self.product_adopter_root_prefixes
            ),
        }

    def cel_policy(self) -> dict[str, object]:
        """Project the immutable declaration fields visible to CEL predicates."""
        return cast(
            "dict[str, object]",
            self.model_dump(
                mode="json",
                exclude={
                    "id",
                    "source_refs",
                    "adopter_specific_product_dirs_allowed",
                    "ignore_boundary",
                    "lifecycle_class",
                    "cel_rule",
                },
            ),
        )


def _prefix_key(item: TopologyPrefix) -> str:
    return item.prefix


def load_generated_artifact_topology_declaration() -> GeneratedArtifactTopologyDeclaration:
    """Load executable policy from the same package as its interpreting code."""
    source = resources.files(__package__).joinpath("topology.toml")
    payload = tomllib.loads(source.read_text(encoding="utf-8"))
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


def artifact_origin(
    path: Path | str,
    declaration: GeneratedArtifactTopologyDeclaration,
) -> str:
    """Resolve declared lifecycle ownership without inferring provenance from format."""
    rel = normalize_artifact_path(path)
    return next(
        (
            item.id
            for item in declaration.lifecycle_class
            if any(_matches_prefix(rel, home) for home in item.homes)
        ),
        "unclassified",
    )


def _cel_rule_context(rule: TopologyCelRule) -> dict[str, object]:
    """Project one rule's declared selector facts into the CEL activation."""
    return {"prefix_group": rule.prefix_group}


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


def _topology_policy(
    rel: str,
    *,
    origin: str,
    declaration: GeneratedArtifactTopologyDeclaration,
) -> dict[str, Any] | None:
    generated = origin != "unclassified"
    facts: dict[str, object] = {"path": rel, "origin": origin, "generated": generated}
    policy = declaration.cel_policy()
    for rule in declaration.cel_rule:
        rule_context = _cel_rule_context(rule)
        if not evaluate_cel_predicate(
            rule.expression, facts=facts, policy=policy, rule=rule_context
        ):
            continue
        matched = _matched_prefix(rule, rel, declaration)
        return _policy(
            path=rel,
            decision=rule.decision,
            boundary=rule.boundary or matched.get("boundary", ""),
            generated=generated,
            required_gap=_gap(
                rule.required_gap_prefix or matched.get("required_gap_prefix", ""),
                rel,
            ),
        )
    return None


def _matched_prefix(
    rule: TopologyCelRule,
    rel: str,
    declaration: GeneratedArtifactTopologyDeclaration,
) -> dict[str, str]:
    """Return metadata for the first matching declared prefix group item."""
    if not rule.prefix_group:
        return {}
    prefixes = cast("tuple[TopologyPrefix, ...]", getattr(declaration, rule.prefix_group))
    return next(
        (
            {"boundary": item.boundary, "required_gap_prefix": item.required_gap_prefix}
            for item in prefixes
            if _matches_prefix(rel, item.prefix)
        ),
        {},
    )


@lru_cache(maxsize=4096)
def _cached_path_policy(
    rel: str,
    declaration: GeneratedArtifactTopologyDeclaration,
    origin: str,
) -> tuple[tuple[str, Any], ...]:
    """Cache immutable declaration decisions for repeated repository readers."""
    origin = artifact_origin(rel, declaration) if origin == "unclassified" else origin
    generated = origin != "unclassified"
    candidate = _topology_policy(rel, origin=origin, declaration=declaration)
    policy = candidate or _policy(
        path=rel,
        decision="ignore",
        boundary=declaration.ignore_boundary,
        generated=generated,
    )
    return tuple((policy | {"origin": origin}).items())


def path_policy_from_declaration(
    path: Path | str,
    declaration: GeneratedArtifactTopologyDeclaration,
    *,
    origin: str = "unclassified",
) -> dict[str, Any]:
    """Classify a repository-relative path under the generated topology contract."""
    rel = normalize_artifact_path(path)
    # Return a new mapping: callers receive a normal mutable public payload while
    # the cached decision remains immutable and cannot leak mutation across reads.
    return dict(_cached_path_policy(rel, declaration, origin))


def path_policy_for(path: Path | str) -> dict[str, Any]:
    """Classify a repository-relative path under the generated topology contract."""
    return path_policy_from_declaration(path, load_generated_artifact_topology_declaration())
