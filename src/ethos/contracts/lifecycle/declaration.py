"""Typed declarations for lifecycle policy, PlanIR actions, and leases."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Literal
from typing import Self

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

from ethos.contracts.plan import PlanIR
from ethos.contracts.plan import PlanNode
from ethos.contracts.plan import compile_plan
from ethos.contracts.system.contracts import load_system_contract

if TYPE_CHECKING:
    from ethos.contracts.semantic import ChangeContract
    from ethos.contracts.semantic import RepositoryFacts

_LEASE_TRANSITION_MATRIX_INVALID = "lease_transition_matrix_invalid"
_TRANSITION_POLICY_MATRIX_INVALID = "transition_policy_matrix_invalid"
_PLAN_ACTION_MATRIX_INVALID = "plan_action_matrix_invalid"


@dataclass(frozen=True, slots=True)
class LeaseTransitionSpec:
    """One exact operation-owned Lease transition contract."""

    effect_fields: tuple[str, ...]
    kind: Literal["refresh", "offer", "accept"]
    actor_field: Literal["holder_ref", "target_holder_ref"]
    blocks_contrary_decision: bool


LEASE_TRANSITION_MATRIX = {
    "renew": LeaseTransitionSpec(
        effect_fields=(
            "holder_ref",
            "expected_epoch",
            "expected_expires_at",
            "expected_payload_sha256",
            "ttl_seconds",
        ),
        kind="refresh",
        actor_field="holder_ref",
        blocks_contrary_decision=False,
    ),
    "resume": LeaseTransitionSpec(
        effect_fields=(
            "holder_ref",
            "expected_epoch",
            "expected_expires_at",
            "expected_payload_sha256",
            "ttl_seconds",
        ),
        kind="refresh",
        actor_field="holder_ref",
        blocks_contrary_decision=True,
    ),
    "handoff_offer": LeaseTransitionSpec(
        effect_fields=(
            "holder_ref",
            "expected_epoch",
            "expected_expires_at",
            "expected_payload_sha256",
            "target_holder_ref",
        ),
        kind="offer",
        actor_field="holder_ref",
        blocks_contrary_decision=False,
    ),
    "handoff_accept": LeaseTransitionSpec(
        effect_fields=(
            "holder_ref",
            "target_holder_ref",
            "offer_id",
            "expected_epoch",
            "expected_expires_at",
            "expected_payload_sha256",
            "holder_quiesced",
            "ttl_seconds",
        ),
        kind="accept",
        actor_field="target_holder_ref",
        blocks_contrary_decision=False,
    ),
}


class _Declaration(BaseModel):
    """Strict immutable base for lifecycle declarations."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class TransitionPolicy(_Declaration):
    """One declaration-owned policy interpreted only by the pure reducer."""

    id: str = Field(min_length=1)
    applied_state: str = Field(min_length=1)
    planned_state: str = "planned"
    current_state: str = ""
    required_role: str = ""
    role_gap: str = ""
    dirty_gap: str = ""
    authorization_required: bool = False
    expected_head_required: bool = False
    head_mismatch_gap: str = "expect_head_mismatch"
    untracked_gap: str = ""
    dry_run_commands: tuple[str, ...] = Field(default=(), strict=False)


class LeaseTransitionDeclaration(TransitionPolicy):
    """One local lease operation and its exact effect binding."""

    effect_fields: tuple[str, ...] = Field(min_length=1, strict=False)
    actor_field: Literal["holder_ref", "target_holder_ref"]
    blocks_contrary_decision: bool = False

    @field_validator("effect_fields")
    @classmethod
    def compile_effect_fields(cls, fields: tuple[str, ...]) -> tuple[str, ...]:
        if any(not field for field in fields) or len(fields) != len(set(fields)):
            raise ValueError(_LEASE_TRANSITION_MATRIX_INVALID)
        return fields

    @property
    def spec(self) -> LeaseTransitionSpec:
        """Return the exact operation-owned transition specification."""
        transition = LEASE_TRANSITION_MATRIX.get(self.id)
        if (
            transition is None
            or self.effect_fields != transition.effect_fields
            or self.actor_field != transition.actor_field
            or self.blocks_contrary_decision != transition.blocks_contrary_decision
        ):
            raise ValueError(_LEASE_TRANSITION_MATRIX_INVALID)
        return transition

    @property
    def kind(self) -> Literal["refresh", "offer", "accept"]:
        """Project the effect kind from the singular transition matrix."""
        return self.spec.kind

    @model_validator(mode="after")
    def bind_actor_to_effect(self) -> Self:
        _ = self.spec
        return self


class PlanAction(_Declaration):
    """One declared root action compiled into PlanIR."""

    id: str = Field(min_length=1)
    kind: Literal["check", "decision", "effect"]
    enforcement: Literal["guarded", "evidence-only"]
    requires: tuple[str, ...] = ()
    produces: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_action(self) -> Self:
        if self.kind == "decision" and self.enforcement == "evidence-only":
            raise ValueError(_PLAN_ACTION_MATRIX_INVALID)
        return self

    def to_plan_node(self, producers: dict[str, str]) -> PlanNode:
        """Compile this action into one PlanIR node."""
        return PlanNode(
            id=self.id,
            kind=self.kind,
            command=("ethos", self.id, "--json"),
            depends_on=tuple(
                dict.fromkeys(
                    producer
                    for requirement in self.requires
                    if (producer := producers.get(requirement)) and producer != self.id
                )
            ),
        )

    def external_requirements(self, producers: dict[str, str]) -> tuple[str, ...]:
        """Return facts supplied outside this PlanIR action set."""
        return tuple(
            dict.fromkeys(
                requirement for requirement in self.requires if requirement not in producers
            )
        )


class LifecycleContract(_Declaration):
    """The singular declaration for lifecycle policy and PlanIR compilation."""

    schema_path: str = Field(alias="schema")
    transition_policy: tuple[TransitionPolicy, ...]
    lease_transition: tuple[LeaseTransitionDeclaration, ...]
    node: tuple[PlanAction, ...]

    @field_validator("lease_transition")
    @classmethod
    def validate_lease_transitions(
        cls, value: tuple[LeaseTransitionDeclaration, ...]
    ) -> tuple[LeaseTransitionDeclaration, ...]:
        operations = tuple(item.id for item in value)
        if operations != tuple(LEASE_TRANSITION_MATRIX):
            raise ValueError(_LEASE_TRANSITION_MATRIX_INVALID)
        return value

    @field_validator("transition_policy")
    @classmethod
    def validate_transition_policies(
        cls, value: tuple[TransitionPolicy, ...]
    ) -> tuple[TransitionPolicy, ...]:
        identifiers = tuple(item.id for item in value)
        if len(identifiers) != len(set(identifiers)):
            raise ValueError(_TRANSITION_POLICY_MATRIX_INVALID)
        return value

    @field_validator("node")
    @classmethod
    def validate_plan_actions(cls, value: tuple[PlanAction, ...]) -> tuple[PlanAction, ...]:
        identifiers = tuple(item.id for item in value)
        if len(identifiers) != len(set(identifiers)):
            raise ValueError(_PLAN_ACTION_MATRIX_INVALID)
        return value

    def policy(self, identifier: str) -> TransitionPolicy:
        """Return one exact transition policy or fail closed."""
        policy = next((item for item in self.transition_policy if item.id == identifier), None)
        if policy is None:
            message = f"transition_policy_unknown:{identifier}"
            raise ValueError(message)
        return policy

    def plan(
        self,
        *,
        contract: ChangeContract,
        facts: RepositoryFacts,
        node_ids: tuple[str, ...] | None = None,
    ) -> PlanIR:
        """Compile the selected lifecycle actions into deterministic PlanIR."""
        requested = set(node_ids or ())
        selected = (
            self.node
            if node_ids is None
            else tuple(item for item in self.node if item.id in requested)
        )
        selected_ids = {item.id for item in selected}
        missing = (
            ()
            if node_ids is None
            else tuple(
                f"lifecycle_plan_action_missing:{identifier}"
                for identifier in node_ids
                if identifier not in selected_ids
            )
        )
        producers: dict[str, str] = {}
        for item in self.node:
            for fact in item.produces:
                producers.setdefault(fact, item.id)
        external_missing = tuple(
            f"lifecycle_external_fact_missing:{item.id}:{requirement}"
            for item in selected
            for requirement in item.external_requirements(producers)
            if not facts.values.get(requirement)
        )
        policy_digest = hashlib.sha256(
            json.dumps(
                self.model_dump(mode="json", by_alias=True),
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        return compile_plan(
            contract,
            facts,
            tuple(item.to_plan_node(producers) for item in selected),
            policy_digest=policy_digest,
            validation_issues=(*missing, *external_missing),
        )


def load_lifecycle_declaration(root: Path | str | None = None) -> LifecycleContract:
    """Load the source-bound lifecycle declaration."""
    return LifecycleContract.model_validate(load_system_contract(Path(root or "."), "lifecycle"))
