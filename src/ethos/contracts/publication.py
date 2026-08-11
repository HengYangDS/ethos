"""Typed remote publication effects outside local Git ref transactions."""

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

_PUBLICATION_PERMISSION = "terminal-publication.execute"


class RemotePublicationTarget(BaseModel):
    """One provider-local exact-CAS proposal ref target."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    id: str = Field(min_length=1)
    remote: str = Field(min_length=1)
    target_ref: str = Field(pattern=r"^refs/heads/.+")
    expected: str = Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
    desired: str = Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")


class RemotePublicationEffect(BaseModel):
    """Typed multi-peer proposal payload admitted only by ``TransitionPlan``.

    Each target is a separate provider transaction. The payload records exact
    peer-local CAS coordinates without claiming cross-provider atomicity, but it
    has no execution authority outside the common semantic kernel.
    """

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    schema_version: Literal[1] = 1
    kind: Literal["remote-publication-effect"] = "remote-publication-effect"
    operation: Literal["proposal.create"] = "proposal.create"
    repository_common_dir: str = Field(min_length=1)
    source_head: str = Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
    targets: tuple[RemotePublicationTarget, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_identity(self) -> Self:
        identities = tuple((target.id, target.remote, target.target_ref) for target in self.targets)
        if len(identities) != len(set(identities)):
            message = "remote_publication_target_duplicate"
            raise ValueError(message)
        if any(target.desired != self.source_head for target in self.targets):
            message = "remote_publication_target_source_mismatch"
            raise ValueError(message)
        target_refs = {target.target_ref for target in self.targets}
        if len(target_refs) != 1:
            message = "remote_publication_target_ref_mismatch"
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
        source_head: str,
        targets: tuple[RemotePublicationTarget, ...],
    ) -> RemotePublicationEffect:
        return cls.model_validate(
            {
                "schema_version": 1,
                "kind": "remote-publication-effect",
                "operation": "proposal.create",
                "repository_common_dir": repository_common_dir,
                "source_head": source_head,
                "targets": tuple(target.model_dump(mode="json") for target in targets),
            }
        )


_PUBLICATION_NODE = PlanNode(
    id="remote.ref.compare-and-swap",
    kind="effect",
    command=("git", "push", "--force-with-lease=<exact>"),
)


def compile_remote_publication_plan(
    *,
    commitment: Commitment,
    facts: Facts,
    effect: RemotePublicationEffect,
    prior_attestations: JsonObject,
) -> TransitionPlan:
    """Compile one remote publication through the common semantic kernel."""
    policy = {
        "operation": effect.operation,
        "transaction_scope": "peer-local",
        "cross_provider_atomicity": False,
    }
    projection = effect.model_dump(mode="json")
    gaps = (
        ()
        if _PUBLICATION_PERMISSION in commitment.permissions
        else ("terminal_publication_authority_missing",)
    )
    return TransitionPlan.compile(
        inputs=PlanInputs(
            commitment=commitment.digest(),
            facts=facts.digest(),
            prior_attestations=canonical_json_digest(prior_attestations),
            policy=canonical_json_digest(policy),
            effect=effect.digest(),
        ),
        closure={
            "commitment": commitment.identity_projection(),
            "prior_attestations": prior_attestations,
            "policy": policy,
            "effect": projection,
        },
        permissions=commitment.permissions,
        facts=facts.model_dump(mode="json", exclude={"observed_at"}),
        nodes=(_PUBLICATION_NODE,),
        required_gaps=gaps,
    )


def remote_publication_effect_from_plan(plan: TransitionPlan) -> RemotePublicationEffect:
    """Return the sole admitted remote publication effect carried by a plan."""
    validated = TransitionPlan.model_validate(plan.model_dump(mode="json"))
    if validated.nodes != (_PUBLICATION_NODE,) or validated.verdict != "pass":
        message = "remote_publication_plan_not_admitted"
        raise ValueError(message)
    try:
        effect = RemotePublicationEffect.model_validate(
            mutable_json(validated.effect), strict=False
        )
    except (TypeError, ValueError) as error:
        message = "remote_publication_plan_invalid"
        raise ValueError(message) from error
    if validated.inputs.effect != effect.digest():
        message = "remote_publication_plan_mismatch"
        raise ValueError(message)
    return effect
