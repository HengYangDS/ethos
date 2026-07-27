"""Bounded external identity and hosted-enforcement evidence contracts."""

from __future__ import annotations

import hashlib
import json

from pydantic import AwareDatetime
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator


class IdentityAssertion(BaseModel):
    """Minimum issuer-qualified identity evidence for one policy evaluation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    identity_ref: str = Field(min_length=1)
    issuer: str = Field(min_length=1)
    audience: str = Field(min_length=1)
    verification_method: str = Field(min_length=1)
    valid_from: AwareDatetime
    valid_until: AwareDatetime
    attestation_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    delegation: str = ""

    @model_validator(mode="after")
    def validate_interval(self) -> IdentityAssertion:
        if self.valid_until <= self.valid_from:
            msg = "valid_until must be later than valid_from"
            raise ValueError(msg)
        return self

    def to_payload(self) -> dict[str, object]:
        return {
            **self.model_dump(mode="json"),
            "evidence_boundary": "verified_external_identity_assertion",
            "mints_authority": False,
            "stores_credentials": False,
            "reusable_authorization": False,
        }


class EnforcementReceipt(BaseModel):
    """Hosted mediator receipt for one exact old/new state transition."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: str = Field(min_length=1)
    enforcement_boundary: str = Field(min_length=1)
    action: str = Field(min_length=1)
    resource: str = Field(min_length=1)
    old_value: str = Field(min_length=1)
    new_value: str = Field(min_length=1)
    observed_at: AwareDatetime
    receipt_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    prevention_coverage: str = Field(min_length=1)

    def to_payload(self) -> dict[str, object]:
        return {
            **self.model_dump(mode="json"),
            "hosted_enforcement_proven": True,
            "mints_authority": False,
            "reusable_authorization": False,
            "recheck_required": True,
        }


class IndependentVerificationReceipt(BaseModel):
    """A provider-neutral receipt for one independently re-executed proof floor.

    It deliberately binds an exact source revision and command floor.  It does
    not say that the source is semantically correct, grant authority, or make a
    provider configuration part of repository truth.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    remote: str = Field(min_length=1)
    commit: str = Field(pattern=r"^[a-f0-9]{40,64}$")
    tree: str = Field(pattern=r"^[a-f0-9]{40,64}$")
    action: str = Field(min_length=1)
    proof_floor_id: str = Field(min_length=1)
    proof_floor_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    policy_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    implementation_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    result: str = Field(pattern=r"^(pass|fail)$")
    issuer: str = Field(min_length=1)
    key_id: str = Field(min_length=1)
    signature_algorithm: str = Field(min_length=1)
    signature: str = Field(min_length=1)
    issued_at: AwareDatetime
    valid_until: AwareDatetime
    payload_digest: str = Field(pattern=r"^[a-f0-9]{64}$|^$")

    @model_validator(mode="after")
    def validate_receipt(self) -> IndependentVerificationReceipt:
        if self.valid_until <= self.issued_at:
            msg = "valid_until must be later than issued_at"
            raise ValueError(msg)
        if self.payload_digest and self.payload_digest != self.canonical_payload_digest():
            msg = "payload_digest does not match canonical receipt payload"
            raise ValueError(msg)
        return self

    def canonical_payload_digest(self) -> str:
        payload = self.model_dump(mode="json", exclude={"signature", "payload_digest"})
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def to_payload(self) -> dict[str, object]:
        return {
            **self.model_dump(mode="json"),
            "evidence_boundary": "independent_exact_proof_floor_reexecution",
            "mints_authority": False,
            "semantic_correctness_proven": False,
            "reusable_authorization": False,
        }
