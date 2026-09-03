"""Immutable contracts for resumable Work Lane retirement."""

from __future__ import annotations

from typing import ClassVar
from typing import Literal
from typing import Self

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator

from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.value import FrozenTuple
from ethos.contracts.value import JsonObject

RetirementEffect = Literal["remove_worktree", "delete_ref", "revoke_lease"]
CarrierState = Literal["expected", "absent", "moved", "unavailable"]


def _fail(reason: str) -> None:
    raise ValueError(reason)


class LinkedRetirementRequest(BaseModel):
    """Exact request for one linked Work Lane retirement transition."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, strict=True, extra="forbid")

    branch: str | None = None
    path: str | None = None
    expect_head: str | None = None
    absorbed_by: str = ""
    reason: str = ""
    authorize: bool = False
    apply: bool = False


class RetirementObservation(BaseModel):
    """Fresh native state for the carriers owned by one retirement."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, strict=True, extra="forbid")

    worktree_state: CarrierState
    ref_state: CarrierState
    lease_state: CarrierState
    accepted_state: CarrierState = "expected"


class RetirementOperation(BaseModel):
    """One immutable terminal intent for a Work Lane retirement."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, strict=True, extra="forbid")

    schema_version: Literal[1] = 1
    kind: Literal["lane-retirement-operation"] = "lane-retirement-operation"
    repository_common_dir: str = Field(min_length=1)
    repository_identity: str = ""
    control_root: str = Field(min_length=1)
    execution_root: str = ""
    mode: Literal["landed", "superseded", "abandon"]
    branch: str = Field(min_length=1)
    head: str = Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
    tree: str = Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
    accepted_branch: str = Field(min_length=1)
    accepted_head: str = Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
    worktree_path: str = ""
    worktree_initial: Literal["linked", "unbound"]
    lease_state: Literal["valid", "expired", "missing"]
    lease: JsonObject
    authority: JsonObject
    reason: JsonObject
    git_plan: JsonObject
    effects: FrozenTuple[RetirementEffect] = ()

    @model_validator(mode="after")
    def derive_effects(self) -> Self:
        expected = (
            *(("remove_worktree",) if self.worktree_initial == "linked" else ()),
            "delete_ref",
            *(("revoke_lease",) if self.lease_state != "missing" else ()),
        )
        if self.effects and self.effects != expected:
            _fail("retirement_operation_effects_invalid")
        if self.worktree_initial == "linked" and not self.worktree_path:
            _fail("retirement_operation_worktree_path_missing")
        if self.mode == "abandon" and not self.reason:
            _fail("lane_abandonment_reason_invalid")
        if not self.execution_root:
            object.__setattr__(self, "execution_root", self.control_root)
        object.__setattr__(self, "effects", expected)
        return self

    def digest(self) -> str:
        """Return the content identity of this immutable operation."""
        return canonical_json_digest(self.model_dump(mode="json"))


class RetirementProgress(BaseModel):
    """Pure projection of one operation against current native carriers."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, strict=True, extra="forbid")

    schema_version: Literal[1] = 1
    kind: Literal["lane-retirement-progress"] = "lane-retirement-progress"
    request_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    state: Literal["ready", "partial_transition", "terminal"]
    observation: RetirementObservation
    completed_effects: FrozenTuple[RetirementEffect]
    remaining_effects: FrozenTuple[RetirementEffect]
