"""Bounded external identity and hosted-enforcement evidence contracts."""

from __future__ import annotations

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
            raise ValueError("valid_until must be later than valid_from")
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
