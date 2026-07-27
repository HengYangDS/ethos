from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from dataclasses import field
from typing import Any

SCHEMA_VERSION = 1


def stable_digest(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class Rule:
    id: str
    owner: str
    authority_ref: str
    contract_ref: str
    path_globs: tuple[str, ...]
    severity: str
    required_gates: tuple[str, ...]
    stop_condition: str
    version: int = 1
    profile_layers: tuple[str, ...] = ()
    subject: str = ""
    evidence_requirements: tuple[str, ...] = ()
    non_waivable: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "version": self.version,
            "owner": self.owner,
            "authority_ref": self.authority_ref,
            "contract_ref": self.contract_ref,
            "path_globs": list(self.path_globs),
            "severity": self.severity,
            "required_gates": list(self.required_gates),
            "stop_condition": self.stop_condition,
        }
        if self.profile_layers:
            payload["profile_layers"] = list(self.profile_layers)
        if self.subject:
            payload["subject"] = self.subject
        if self.evidence_requirements:
            payload["evidence_requirements"] = list(self.evidence_requirements)
        if self.non_waivable:
            payload["non_waivable"] = True
        return payload


@dataclass(frozen=True, slots=True)
class RuleSet:
    id: str
    profile_layers: tuple[str, ...]
    rules: tuple[Rule, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "id": self.id,
            "profile_layers": list(self.profile_layers),
            "rules": [rule.to_dict() for rule in self.rules],
        }

    @property
    def digest(self) -> str:
        return stable_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class PolicyException:
    id: str
    rule_id: str
    scope: str
    owner: str
    approver: str
    reason: str
    evidence_ref: str
    created_at: str
    expires_at: str
    status: str = "active"
    max_ttl: str = ""
    digest: str = field(default="")

    def to_dict(self) -> dict[str, Any]:
        base: dict[str, Any] = {
            "id": self.id,
            "rule_id": self.rule_id,
            "scope": self.scope,
            "owner": self.owner,
            "approver": self.approver,
            "reason": self.reason,
            "evidence_ref": self.evidence_ref,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "status": self.status,
        }
        if self.max_ttl:
            base["max_ttl"] = self.max_ttl
        base["digest"] = self.digest or stable_digest(base)
        return base
