"""Strict portable rule and rule-set contracts."""

import operator
from collections import Counter
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator

from ethos.contracts.value import FrozenTuple

SCHEMA_VERSION = 1


class _RuleModel(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")


class Rule(_RuleModel):
    id: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    authority_ref: str = Field(min_length=1)
    contract_ref: str = Field(min_length=1)
    path_globs: FrozenTuple[str] = Field(min_length=1)
    severity: Literal["advisory", "blocking"]
    required_gates: FrozenTuple[str]
    stop_condition: str = Field(min_length=1)
    version: int = Field(default=1, ge=1)
    profile_layers: FrozenTuple[str] = Field(default=(), exclude_if=operator.not_)
    subject: str = Field(default="", exclude_if=operator.not_)
    evidence_requirements: FrozenTuple[str] = Field(default=(), exclude_if=operator.not_)
    non_waivable: bool = Field(default=False, exclude_if=operator.not_)


class RuleSet(_RuleModel):
    schema_version: Literal[1] = SCHEMA_VERSION
    id: str = Field(min_length=1)
    profile_layers: FrozenTuple[str]
    rules: FrozenTuple[Rule]

    @field_validator("rules")
    @classmethod
    def require_unique_rule_identity(cls, rules: tuple[Rule, ...]) -> tuple[Rule, ...]:
        """Resolve each active identity to one definition, never an implicit winner."""
        counts = Counter(rule.id for rule in rules)
        conflicts = sorted(identity for identity, count in counts.items() if count > 1)
        if conflicts:
            message = "rule_identity_conflict:" + ",".join(conflicts)
            raise ValueError(message)
        return rules
