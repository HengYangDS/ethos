"""Pure compilation of adaptive review lenses from exact repository facts."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Literal
from typing import Self

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import TypeAdapter
from pydantic import ValidationError
from pydantic import model_validator

from ethos._resources import declaration_text
from ethos.contracts.plan import dependency_order
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.value import FrozenTuple
from ethos.contracts.value import JsonObject
from ethos.contracts.value import mutable_json
from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import reduce_verdicts

ReviewPhase = Literal["pre-implementation", "post-implementation"]
_ALWAYS_ESCALATE = "final-product-judgment"
DECLARATION_PATH = Path("system/review-lenses.toml")
_DECLARATION_RESOURCE = "data/review_lenses.toml"


class _ReviewModel(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")


class ReviewLens(_ReviewModel):
    """One declaration-owned, non-authorizing review capability."""

    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    phases: FrozenTuple[ReviewPhase] = Field(min_length=1)
    requires: FrozenTuple[str] = ()
    triggers: FrozenTuple[str] = ()
    owner: str = Field(min_length=1)
    output_schema: str = Field(min_length=1)
    blocking: bool = True
    max_tokens: int = Field(ge=0)
    freshness: Literal["exact-head-tree-inputs"] = "exact-head-tree-inputs"


class ReviewLensDeclaration(_ReviewModel):
    """Closed declaration for one adaptive review method portfolio."""

    id: Literal["review-lenses"] = "review-lenses"
    schema_version: Literal[1] = 1
    source_refs: FrozenTuple[str] = ()
    lenses: FrozenTuple[ReviewLens] = Field(min_length=1)

    @model_validator(mode="after")
    def reject_duplicate_lenses(self) -> Self:
        if len(self.lenses) != len({lens.id for lens in self.lenses}):
            message = "review_lens_duplicate"
            raise ValueError(message)
        return self

    def digest(self) -> str:
        return canonical_json_digest(self.model_dump(mode="json"))


class CompiledReviewLens(_ReviewModel):
    """One selected lens bound to the current review phase."""

    id: str
    owner: str
    output_schema: str
    blocking: bool
    max_tokens: int
    freshness: Literal["exact-head-tree-inputs"]


class ReviewPlan(_ReviewModel):
    """Transient exact-input review closure; it owns no workflow state."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        extra="forbid",
        json_schema_serialization_defaults_required=True,
    )

    schema_version: Literal[1] = 1
    declaration: str = Field(pattern=r"^[a-f0-9]{64}$")
    inputs: str = Field(pattern=r"^[a-f0-9]{64}$")
    head: str = Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
    tree: str = Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
    phase: ReviewPhase
    lenses: FrozenTuple[CompiledReviewLens] = ()
    escalation: FrozenTuple[str] = ()
    verdict: Verdict
    required_gaps: FrozenTuple[str] = ()
    next_action: str = Field(min_length=1)
    user_decision_required: bool = False
    digest: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def validate_digest(self) -> Self:
        if self.digest != canonical_json_digest(self.model_dump(mode="json", exclude={"digest"})):
            message = "review_plan_digest_mismatch"
            raise ValueError(message)
        return self


class ReviewFinding(_ReviewModel):
    """One reproducible finding from a compiled lens."""

    code: str = Field(pattern=r"^[a-z][a-z0-9-]*(?::[^:]+)*$")
    message: str = Field(min_length=1)
    locations: FrozenTuple[str] = ()
    repairable: bool


class ReviewResult(_ReviewModel):
    """Exact-plan lens output that cannot mint transition authority."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        extra="forbid",
        json_schema_serialization_defaults_required=True,
    )

    schema_version: Literal[1] = 1
    review_plan: str = Field(pattern=r"^[a-f0-9]{64}$")
    inputs: str = Field(pattern=r"^[a-f0-9]{64}$")
    head: str = Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
    tree: str = Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
    phase: ReviewPhase
    lens: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    verifier: str = Field(min_length=1)
    verdict: Verdict
    findings: FrozenTuple[ReviewFinding] = ()
    evidence_refs: FrozenTuple[str] = ()
    next_action: str = Field(min_length=1)
    mints_authority: Literal[False] = False


class ReviewDecision(_ReviewModel):
    """Closed reduction over one exact review plan and its independent results."""

    review_plan: str = Field(pattern=r"^[a-f0-9]{64}$")
    verdict: Verdict
    state: Literal["reviewed", "repair", "await-user", "gapped"]
    required_gaps: FrozenTuple[str] = ()
    next_action: str = Field(min_length=1)
    user_decision_required: bool = False


_REVIEW_RESULTS_ADAPTER = TypeAdapter(tuple[ReviewResult, ...])


def load_review_lens_declaration(path: Path | None = None) -> ReviewLensDeclaration:
    """Load one tracked review-lens declaration without creating runtime state."""
    source = path or DECLARATION_PATH
    payload = tomllib.loads(
        declaration_text(source, resource=_DECLARATION_RESOURCE, canonical=DECLARATION_PATH)
    )
    payload["lenses"] = payload.pop("lens", ())
    return ReviewLensDeclaration.model_validate(payload)


def load_review_results(path: str | Path) -> tuple[ReviewResult, ...]:
    """Load one portable JSON result set without creating repository state."""
    source = Path(path)
    try:
        return _REVIEW_RESULTS_ADAPTER.validate_json(source.read_bytes())
    except (OSError, ValidationError) as error:
        message = "review_results_invalid"
        raise ValueError(message) from error


def compile_review_plan(
    declaration: ReviewLensDeclaration,
    facts: dict[str, object],
) -> ReviewPlan:
    """Compile workload, risk, intent, and scope facts into a canonical review set."""
    normalized = mutable_json(facts)
    if not isinstance(normalized, dict):
        message = "review_facts_invalid"
        raise TypeError(message)
    phase = _phase(normalized)
    facts_gaps = _facts_gaps(normalized)
    selected = {
        lens.id
        for lens in declaration.lenses
        if phase in lens.phases and _selected(lens, normalized)
    }
    by_id = {lens.id: lens for lens in declaration.lenses}
    gaps = [*facts_gaps, *_dependency_gaps(selected, by_id)]
    ordered = _ordered(selected, by_id, gaps)
    ambiguities = _strings(normalized.get("ambiguities"))
    if ambiguities:
        gaps.append("review_intent_ambiguous")
    escalation = _escalation(normalized, ambiguities)
    verdict: Verdict = (
        "block"
        if any(gap != "review_intent_ambiguous" for gap in gaps)
        else ("unknown" if gaps else "pass")
    )
    payload = {
        "schema_version": 1,
        "declaration": declaration.digest(),
        "inputs": canonical_json_digest(normalized),
        "head": normalized.get("head", ""),
        "tree": normalized.get("tree", ""),
        "phase": phase,
        "lenses": [
            CompiledReviewLens(
                id=lens.id,
                owner=lens.owner,
                output_schema=lens.output_schema,
                blocking=lens.blocking,
                max_tokens=lens.max_tokens,
                freshness=lens.freshness,
            ).model_dump(mode="json")
            for lens in ordered
        ],
        "escalation": list(escalation),
        "verdict": verdict,
        "required_gaps": list(dict.fromkeys(gaps)),
        "next_action": _next_action(gaps),
        "user_decision_required": bool(ambiguities),
    }
    return ReviewPlan.model_validate(payload | {"digest": canonical_json_digest(payload)})


def reduce_review_results(
    plan: ReviewPlan,
    results: tuple[ReviewResult, ...],
) -> ReviewDecision:
    """Reduce exact-bound lens outputs; clear repairs precede human escalation."""
    selected_ids = {lens.id for lens in plan.lenses}
    result_ids = [result.lens for result in results]
    duplicates = {lens_id for lens_id in result_ids if result_ids.count(lens_id) > 1}
    gaps = [f"review_result_duplicate:{lens_id}" for lens_id in sorted(duplicates)]
    gaps.extend(
        f"review_result_unselected:{lens_id}" for lens_id in sorted(set(result_ids) - selected_ids)
    )
    by_lens = {
        result.lens: result
        for result in results
        if result.lens in selected_ids and result.lens not in duplicates
    }
    admitted: list[ReviewResult] = []
    for lens in plan.lenses:
        result = by_lens.get(lens.id)
        if lens.id in duplicates:
            continue
        if result is None:
            gaps.append(f"review_result_missing:{lens.id}")
        elif not _result_matches(plan, result):
            gaps.append(f"review_result_binding_mismatch:{lens.id}")
        else:
            admitted.append(result)
    unknown = [result for result in admitted if result.verdict == "unknown"]
    repairable = [result for result in admitted if _repairable(result)]
    blocked = [result for result in admitted if result.verdict == "block"]
    if gaps:
        return _review_decision(
            plan, "block", "gapped", gaps, "rerun the missing or stale review lenses"
        )
    if repairable:
        return _review_decision(plan, "block", "repair", (), repairable[0].next_action)
    if unknown:
        return _review_decision(
            plan,
            "unknown",
            "await-user",
            (),
            unknown[0].next_action,
            user_decision_required=True,
        )
    if blocked:
        return _review_decision(plan, "block", "gapped", (), blocked[0].next_action)
    verdict = reduce_verdicts(*(result.verdict for result in admitted))
    return _review_decision(plan, verdict, "reviewed", (), "continue the governed lifecycle")


def _phase(facts: JsonObject) -> ReviewPhase:
    phase = facts.get("phase")
    if phase not in {"pre-implementation", "post-implementation"}:
        message = "review_phase_invalid"
        raise ValueError(message)
    return phase


def _strings(value: object) -> tuple[str, ...]:
    return tuple(str(item) for item in value) if isinstance(value, tuple | list) else ()


def _selected(lens: ReviewLens, facts: JsonObject) -> bool:
    if not lens.triggers:
        return True
    signals = {
        *_strings(facts.get("risks")),
        *_strings(facts.get("affected_capabilities")),
    }
    changed_paths = _strings(facts.get("changed_paths"))
    return bool(signals & set(lens.triggers)) or any(
        Path(path).match(trigger) for path in changed_paths for trigger in lens.triggers
    )


def _facts_gaps(facts: JsonObject) -> list[str]:
    requirements = set(_strings(facts.get("requirements")))
    raw_edges = facts.get("requirement_edges")
    edges = raw_edges if isinstance(raw_edges, tuple | list) else ()
    mapped = {str(edge.get("requirement")) for edge in edges if isinstance(edge, dict)}
    gaps = ["review_traceability_incomplete"] if requirements - mapped else []
    if _strings(facts.get("conflicts")):
        gaps.append("review_intent_conflict")
    return gaps


def _dependency_gaps(
    selected: set[str],
    by_id: dict[str, ReviewLens],
) -> list[str]:
    gaps: list[str] = []
    pending = list(selected)
    while pending:
        lens = by_id[pending.pop()]
        for required in lens.requires:
            if required not in by_id:
                gaps.append(f"review_lens_dependency_missing:{lens.id}:{required}")
            elif required not in selected:
                selected.add(required)
                pending.append(required)
    return gaps


def _ordered(
    selected: set[str],
    by_id: dict[str, ReviewLens],
    gaps: list[str],
) -> tuple[ReviewLens, ...]:
    ordered_ids = tuple(lens.id for lens in by_id.values() if lens.id in selected)
    graph = {
        lens_id: tuple(
            dict.fromkeys(
                (
                    *(required for required in by_id[lens_id].requires if required in selected),
                    *(ordered_ids[index - 1 : index] if index else ()),
                )
            )
        )
        for index, lens_id in enumerate(ordered_ids)
    }
    try:
        return tuple(by_id[lens_id] for lens_id in dependency_order(graph))
    except ValueError:
        gaps.append("review_lens_dependency_cycle")
        return ()


def _escalation(facts: JsonObject, ambiguities: tuple[str, ...]) -> tuple[str, ...]:
    risks = set(_strings(facts.get("risks")))
    reasons = ["unresolved-intent"] if ambiguities else []
    if "trust-bound-publication" in risks:
        reasons.append("trust-bound-publication")
    if "irreversible" in risks:
        reasons.append("irreversible-effect")
    reasons.append(_ALWAYS_ESCALATE)
    return tuple(reasons)


def _next_action(gaps: list[str]) -> str:
    if "review_intent_ambiguous" in gaps or "review_intent_conflict" in gaps:
        return "resolve the selected OpenSpec intent before implementation"
    if "review_traceability_incomplete" in gaps:
        return "map every requirement to its task and proof"
    if gaps:
        return "repair the review-lens declaration"
    return "execute the compiled review lenses and bind each result to this plan"


def _result_matches(plan: ReviewPlan, result: ReviewResult) -> bool:
    return (
        result.review_plan == plan.digest
        and result.inputs == plan.inputs
        and result.head == plan.head
        and result.tree == plan.tree
        and result.phase == plan.phase
        and result.mints_authority is False
    )


def _repairable(result: ReviewResult) -> bool:
    return (
        result.verdict == "block"
        and bool(result.findings)
        and all(finding.repairable for finding in result.findings)
    )


def _review_decision(
    plan: ReviewPlan,
    verdict: Verdict,
    state: Literal["reviewed", "repair", "await-user", "gapped"],
    gaps: tuple[str, ...] | list[str],
    next_action: str,
    *,
    user_decision_required: bool = False,
) -> ReviewDecision:
    return ReviewDecision(
        review_plan=plan.digest,
        verdict=verdict,
        state=state,
        required_gaps=tuple(gaps),
        next_action=next_action,
        user_decision_required=user_decision_required,
    )


def review_schema_documents() -> dict[str, dict[str, object]]:
    """Generate language-neutral review contracts from their typed owners."""
    documents: dict[str, dict[str, object]] = {}
    for name, model in {
        "review-plan.schema.json": ReviewPlan,
        "review-result.schema.json": ReviewResult,
    }.items():
        schema = model.model_json_schema(mode="serialization")
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema["$id"] = f"https://ethos.local/schemas/{name}"
        schema["title"] = f"ETHOS {model.__name__}"
        documents[name] = schema
    return documents
