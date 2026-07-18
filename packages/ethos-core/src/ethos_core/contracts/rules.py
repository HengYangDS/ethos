from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from dataclasses import field
from typing import Any

SCHEMA_VERSION = 1
REQUIRED_SOURCE_FACT_NAMES = (
    "worktree",
    "prewrite",
    "openspec_state",
    "claim_state",
    "evidence_freshness",
    "host_readiness",
    "command_registry",
    "projection_drift",
)


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
class RuleFactSnapshot:
    phase: str
    head: str
    facts: dict[str, dict[str, Any]]
    schema_version: int = SCHEMA_VERSION
    source_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        base = {
            "schema_version": self.schema_version,
            "phase": self.phase,
            "head": self.head,
            "facts": self.facts,
            "source_refs": list(self.source_refs),
        }
        return {**base, "digest": stable_digest(base)}

    @property
    def digest(self) -> str:
        return str(self.to_dict()["digest"])


@dataclass(frozen=True, slots=True)
class RuleEvalRequest:
    phase: str
    changed_paths: tuple[str, ...] = ()
    mutation: bool = False
    authorized: bool = False
    actor: str = "local"
    scope: str = "repository"

    def to_fact_snapshot(self, *, head: str, source_refs: tuple[str, ...] = ()) -> RuleFactSnapshot:
        facts: dict[str, dict[str, Any]] = {
            name: {
                "owner": "ethos-source-required",
                "fresh": False,
                "available": False,
                "value": {"required": True},
            }
            for name in REQUIRED_SOURCE_FACT_NAMES
        }
        facts.update(
            {
                "changed_paths": {
                    "owner": "ethos-adapters",
                    "fresh": True,
                    "available": True,
                    "value": list(self.changed_paths),
                },
                "mutation": {
                    "owner": "ethos-cli",
                    "fresh": True,
                    "available": True,
                    "value": self.mutation,
                },
                "authorization": {
                    "owner": "ethos-cli",
                    "fresh": True,
                    "available": True,
                    "value": self.authorized,
                },
                "actor": {
                    "owner": "ethos-cli",
                    "fresh": True,
                    "available": True,
                    "value": self.actor,
                },
                "scope": {
                    "owner": "ethos-cli",
                    "fresh": True,
                    "available": True,
                    "value": self.scope,
                },
            }
        )
        return RuleFactSnapshot(
            phase=self.phase,
            head=head,
            source_refs=source_refs,
            facts=facts,
        )


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


@dataclass(frozen=True, slots=True)
class RuleAttestation:
    head: str
    evaluation_digest: str
    rule_set_digest: str
    compiled_policy_digest: str
    fact_snapshot_digest: str
    actor: str
    scope: str
    runner_identity: str
    schema_version: int = SCHEMA_VERSION
    input: dict[str, Any] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "head": self.head,
            "evaluation_digest": self.evaluation_digest,
            "rule_set_digest": self.rule_set_digest,
            "compiled_policy_digest": self.compiled_policy_digest,
            "fact_snapshot_digest": self.fact_snapshot_digest,
            "actor": self.actor,
            "scope": self.scope,
            "runner_identity": self.runner_identity,
            "input": dict(self.input),
            "output": dict(self.output),
        }


def rule_attestation_gaps(
    attestation: dict[str, Any],
    evaluation: dict[str, Any],
) -> tuple[str, ...]:
    """Return machine-readable gaps for an attestation/evaluation pair."""
    checks = {
        "head": ("head", "head"),
        "evaluation_digest": ("evaluation_digest", "digest"),
        "rule_set_digest": ("rule_set_digest", "rule_set_digest"),
        "compiled_policy_digest": ("compiled_policy_digest", "compiled_policy_digest"),
        "fact_snapshot_digest": ("fact_snapshot_digest", "fact_snapshot_digest"),
    }
    gaps: list[str] = []
    for gap_name, (attestation_key, evaluation_key) in checks.items():
        if attestation.get(attestation_key) != evaluation.get(evaluation_key):
            gaps.append(f"rule_attestation_mismatch:{gap_name}")
    if not attestation.get("runner_identity"):
        gaps.append("rule_attestation_runner_missing")
    if not attestation.get("actor"):
        gaps.append("rule_attestation_actor_missing")
    if not attestation.get("scope"):
        gaps.append("rule_attestation_scope_missing")
    input_snapshot = attestation.get("input")
    if not isinstance(input_snapshot, dict):
        gaps.append("rule_attestation_input_missing")
    else:
        input_base = {key: value for key, value in input_snapshot.items() if key != "digest"}
        if input_snapshot.get("digest") != stable_digest(input_base):
            gaps.append("rule_attestation_mismatch:input_digest")
        if input_snapshot.get("digest") != evaluation.get("fact_snapshot_digest"):
            gaps.append("rule_attestation_mismatch:input_snapshot")
        if input_snapshot != evaluation.get("input_snapshot"):
            gaps.append("rule_attestation_mismatch:input")
        facts = input_snapshot.get("facts")
        if isinstance(facts, dict):
            actor_fact = facts.get("actor")
            if isinstance(actor_fact, dict) and actor_fact.get("value") != attestation.get("actor"):
                gaps.append("rule_attestation_mismatch:actor")
            scope_fact = facts.get("scope")
            if isinstance(scope_fact, dict) and scope_fact.get("value") != attestation.get("scope"):
                gaps.append("rule_attestation_mismatch:scope")
    output = attestation.get("output")
    if not isinstance(output, dict):
        gaps.append("rule_attestation_output_missing")
    else:
        if output.get("state") != evaluation.get("state"):
            gaps.append("rule_attestation_mismatch:output_state")
        if output.get("required_gaps") != evaluation.get("required_gaps"):
            gaps.append("rule_attestation_mismatch:output_required_gaps")
        if output.get("required_gates") != evaluation.get("required_gates"):
            gaps.append("rule_attestation_mismatch:output_required_gates")
    return tuple(gaps)
