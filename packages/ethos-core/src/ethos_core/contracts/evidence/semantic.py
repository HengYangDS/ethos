"""Typed semantic-attestation receipt contract."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import AwareDatetime
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator


class SemanticAttestationReceipt(BaseModel):
    """Candidate-external review attestation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal[1]
    kind: Literal["semantic-attestation"]
    claim_id: str = Field(min_length=1)
    evidence_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    scope_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    head: str = Field(pattern=r"^[a-f0-9]{40,64}$")
    reviewer_role: Literal["independent_reviewer"]
    reviewer_ref: str = Field(min_length=1)
    basis: str = Field(min_length=1)
    verdict: Literal["allow"]
    issued_at: AwareDatetime
    valid_until: AwareDatetime
    mints_authority: Literal[False]
    payload_digest: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="before")
    @classmethod
    def validate_payload_digest(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        payload = {key: item for key, item in value.items() if key != "payload_digest"}
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        if value.get("payload_digest") != digest:
            raise ValueError("payload_digest does not match canonical receipt payload")  # noqa: EM101, RUF100, TRY003
        return value
