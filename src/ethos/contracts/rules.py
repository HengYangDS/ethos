"""Strict portable rule and rule-set contracts."""

import hashlib
import json
import operator
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from ethos.contracts.value import FrozenTuple

SCHEMA_VERSION = 1


def stable_digest(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


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

    @property
    def digest(self) -> str:
        return stable_digest(self.model_dump(mode="json"))
