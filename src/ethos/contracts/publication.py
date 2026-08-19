"""Typed exact-object publication effects for remote Git refs."""

from __future__ import annotations

from typing import Literal
from typing import Self

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator

from ethos.contracts.plan import PlanInputs
from ethos.contracts.plan import PlanNode
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.semantic import Commitment
from ethos.contracts.semantic import Facts
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.value import JsonObject
from ethos.contracts.value import mutable_json


class PublicationTarget(BaseModel):
    """One peer-local exact-CAS full-ref target."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    id: str = Field(min_length=1)
    remote: str = Field(min_length=1)
    target_ref: str = Field(pattern=r"^refs/(?:heads|tags)/.+")
    expected: str = Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
    desired: str = Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")


class PublicationEffect(BaseModel):
    """Exact local object projection admitted only by TransitionPlan."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    schema_version: Literal[1] = 1
    kind: Literal["publication-effect"] = "publication-effect"
    operation: Literal["git.ref.compare-and-swap"] = "git.ref.compare-and-swap"
    repository_common_dir: str = Field(min_length=1)
    source_kind: Literal["commit", "annotated-tag"]
    source_object: str = Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
    targets: tuple[PublicationTarget, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_identity(self) -> Self:
        identities = tuple((target.id, target.remote, target.target_ref) for target in self.targets)
        if len(identities) != len(set(identities)):
            message = "publication_target_duplicate"
            raise ValueError(message)
        if any(target.desired != self.source_object for target in self.targets):
            message = "publication_target_source_mismatch"
            raise ValueError(message)
        ref_kinds = {
            "annotated-tag" if target.target_ref.startswith("refs/tags/") else "commit"
            for target in self.targets
        }
        if ref_kinds != {self.source_kind}:
            message = "publication_target_source_kind_mismatch"
            raise ValueError(message)
        return self

    def digest(self) -> str:
        """Return the canonical identity of this exact peer-local CAS effect."""
        return canonical_json_digest(self.model_dump(mode="json"))

    @classmethod
    def compile(
        cls,
        *,
        repository_common_dir: str,
        source_object: str,
        targets: tuple[PublicationTarget, ...],
    ) -> PublicationEffect:
        source_kinds = {
            "annotated-tag" if target.target_ref.startswith("refs/tags/") else "commit"
            for target in targets
        }
        if len(source_kinds) != 1:
            message = "publication_target_ref_kind_mismatch"
            raise ValueError(message)
        return cls.model_validate(
            {
                "schema_version": 1,
                "kind": "publication-effect",
                "operation": "git.ref.compare-and-swap",
                "repository_common_dir": repository_common_dir,
                "source_kind": next(iter(source_kinds)),
                "source_object": source_object,
                "targets": tuple(target.model_dump(mode="json") for target in targets),
            }
        )


_PUBLICATION_NODE = PlanNode(
    id="git.ref.compare-and-swap",
    kind="effect",
    command=("git", "push", "--force-with-lease=<exact>"),
)


def compile_publication_plan(
    *,
    commitment: Commitment,
    facts: Facts,
    effect: PublicationEffect,
    prior_attestations: JsonObject,
) -> TransitionPlan:
    """Compile one exact-object publication through the semantic kernel."""
    effect_digest = effect.digest()
    policy = {
        "operation": effect.operation,
        "effect_digest": effect_digest,
        "transaction_scope": "peer-local",
        "cross_provider_atomicity": False,
    }
    projection = effect.model_dump(mode="json")
    return TransitionPlan.compile(
        inputs=PlanInputs(
            commitment=commitment.digest(),
            facts=facts.digest(),
            prior_attestations=canonical_json_digest(prior_attestations),
            policy=canonical_json_digest(policy),
            effect=effect_digest,
        ),
        closure={
            "commitment": commitment.identity_projection(),
            "prior_attestations": prior_attestations,
            "policy": policy,
            "effect": projection,
        },
        facts=facts.model_dump(mode="json", exclude={"observed_at"}),
        nodes=(_PUBLICATION_NODE,),
    )


def publication_effect_from_plan(plan: TransitionPlan) -> PublicationEffect:
    """Return the sole admitted publication effect carried by a plan."""
    validated = TransitionPlan.model_validate(plan.model_dump(mode="json"))
    if validated.nodes != (_PUBLICATION_NODE,) or validated.verdict != "pass":
        message = "publication_plan_not_admitted"
        raise ValueError(message)
    try:
        effect = PublicationEffect.model_validate(mutable_json(validated.effect), strict=False)
    except (TypeError, ValueError) as error:
        message = "publication_plan_invalid"
        raise ValueError(message) from error
    effect_digest = effect.digest()
    if (
        validated.inputs.effect != effect_digest
        or validated.policy.get("operation") != effect.operation
        or validated.policy.get("effect_digest") != effect_digest
    ):
        message = "publication_plan_mismatch"
        raise ValueError(message)
    return effect
