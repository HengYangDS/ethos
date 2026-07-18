"""Generated artifact topology contract.

The contract is path-oriented and adopter-neutral: it decides where classes of
runtime state, generated proof output, reports, and curated evidence may live
without encoding one adopter, profile, or repository-specific fixture name.
"""

from __future__ import annotations

import tomllib
from functools import lru_cache
from pathlib import Path
from typing import Any
from typing import Literal
from typing import cast

import celpy
from celpy.celtypes import BoolType
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import model_validator

from ethos_core._resources import declaration_text
from ethos_core._resources import resolve_declaration_path

DECLARATION_PATH = Path("system/policies/generated-artifact-topology.toml")
_DECLARATION_RESOURCE = "data/generated_artifact_topology.toml"
_CEL_RULE_IDS = frozenset(
    {
        "generated",
        "product-adopter-root",
        "denied-prefix",
        "denied-root-cache",
        "cache-flat",
        "denied-legacy-generated",
        "runtime-flat",
        "declarative",
        "allowed",
        "review",
        "denied-generated",
        "repo-root-generated",
    }
)


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


class TopologyCelRule(BaseModel):
    """One ordered, restricted CEL predicate for a topology decision."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: Literal[
        "generated",
        "product-adopter-root",
        "denied-prefix",
        "denied-root-cache",
        "cache-flat",
        "denied-legacy-generated",
        "runtime-flat",
        "declarative",
        "allowed",
        "review",
        "denied-generated",
        "repo-root-generated",
    ]
    expression: str
    decision: Literal["classify", "allow", "review", "deny"]
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

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    schema_version: int = 1
    source_refs: tuple[str, ...] = ()
    adopter_specific_product_dirs_allowed: bool = False
    cache_flat_root_prefix: str
    cache_allowed_prefixes: tuple[str, ...]
    runtime_flat_root_prefix: str
    runtime_allowed_prefixes: tuple[str, ...]
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
    cel_rule: tuple[TopologyCelRule, ...]

    @model_validator(mode="after")
    def validate_cel_rules(self) -> GeneratedArtifactTopologyDeclaration:
        """Require the complete ordered topology rule set before evaluation."""
        ids = [rule.id for rule in self.cel_rule]
        if len(ids) != len(set(ids)) or set(ids) != _CEL_RULE_IDS:
            msg = "topology CEL rule ids must be unique and complete"
            raise ValueError(msg)
        generated = next(rule for rule in self.cel_rule if rule.id == "generated")
        if generated.decision != "classify":
            msg = "topology CEL generated rule must classify"
            raise ValueError(msg)
        if any(rule.decision == "classify" for rule in self.cel_rule if rule is not generated):
            msg = "topology CEL only generated may classify"
            raise ValueError(msg)
        return self

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

    def cel_policy(self) -> dict[str, object]:
        """Project the immutable declaration fields visible to CEL predicates."""
        return cast(
            "dict[str, object]",
            self.model_dump(
                mode="json",
                exclude={
                    "id",
                    "schema_version",
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


def _declaration_text(path: Path) -> str:
    return declaration_text(path, resource=_DECLARATION_RESOURCE, canonical=DECLARATION_PATH)


def load_generated_artifact_topology_declaration(
    path: Path | str | None = None,
) -> GeneratedArtifactTopologyDeclaration:
    """Load the generated-artifact topology declaration from TOML."""
    declaration_path = resolve_declaration_path(
        path, canonical=DECLARATION_PATH, module_file=__file__
    )
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


def is_generated_artifact_path(
    path: Path | str,
    declaration: GeneratedArtifactTopologyDeclaration | None = None,
) -> bool:
    """Return whether a path has the shape of generated runtime/proof output."""
    rel = normalize_artifact_path(path)
    topology = declaration or load_generated_artifact_topology_declaration()
    return _topology_rule_matches("generated", rel, topology)


def evaluate_cel_predicate(
    expression: str,
    *,
    facts: dict[str, object],
    policy: dict[str, object],
    rule: dict[str, object],
) -> bool:
    """Evaluate a restricted CEL predicate over immutable topology fact maps."""
    result = _evaluate_cel(expression, facts=facts, policy=policy, rule=rule)
    if not isinstance(result, BoolType):
        msg = "CEL predicate must return a boolean"
        raise TypeError(msg)
    return bool(result)


def _evaluate_cel(
    expression: str,
    *,
    facts: dict[str, object],
    policy: dict[str, object],
    rule: dict[str, object],
) -> object:
    activation = cast(
        "dict[str, object]",
        celpy.json_to_cel({"facts": facts, "policy": policy, "rule": rule}),
    )
    return _cel_program(expression).evaluate(cast("Any", activation))


@lru_cache
def _cel_program(expression: str) -> Any:
    """Compile and cache a declaration-owned CEL predicate."""
    environment = celpy.Environment()
    return environment.program(environment.compile(expression))


def _topology_facts(rel: str) -> dict[str, object]:
    name = rel.rsplit("/", maxsplit=1)[-1]
    return {"path": rel, "name": name, "suffix": Path(name).suffix}


def _topology_rule_matches(
    rule_id: str,
    rel: str,
    declaration: GeneratedArtifactTopologyDeclaration,
) -> bool:
    """Evaluate one named CEL predicate over a normalized topology path."""
    return evaluate_cel_predicate(
        _cel_rule(declaration, rule_id).expression,
        facts=_topology_facts(rel),
        policy=declaration.cel_policy(),
        rule=_cel_rule_context(_cel_rule(declaration, rule_id)),
    )


def _cel_rule(declaration: GeneratedArtifactTopologyDeclaration, rule_id: str) -> TopologyCelRule:
    """Return one declared CEL rule or fail closed when the policy is incomplete."""
    for rule in declaration.cel_rule:
        if rule.id == rule_id:
            return rule
    msg = f"missing topology CEL rule: {rule_id}"
    raise ValueError(msg)


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
    generated: bool,
    declaration: GeneratedArtifactTopologyDeclaration,
) -> dict[str, Any] | None:
    facts = {**_topology_facts(rel), "generated": generated}
    policy = declaration.cel_policy()
    for rule in declaration.cel_rule:
        if rule.decision == "classify":
            continue
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


def path_policy_from_declaration(
    path: Path | str,
    declaration: GeneratedArtifactTopologyDeclaration,
) -> dict[str, Any]:
    """Classify a repository-relative path under the generated topology contract."""
    rel = normalize_artifact_path(path)
    generated = is_generated_artifact_path(rel, declaration)
    candidate = _topology_policy(rel, generated=generated, declaration=declaration)
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
