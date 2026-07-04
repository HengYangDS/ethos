from __future__ import annotations

from dataclasses import dataclass
from typing import Any

CAPABILITY_GRAPH = (
    "source_truth",
    "source_verified_context_projection",
    "quality_gates",
    "claims_and_evidence",
    "campaign_review",
    "assistant_mcp_projection",
    "ignored_local_state_projection",
)

KERNEL_CHAIN = (
    "JudgmentSource",
    "Subject",
    "Commitment",
    "Change",
    "Evidence",
    "Claim",
    "Chronicle",
)

TRUST_LIFECYCLE = (
    "Claim",
    "Boundary",
    "Carrier",
    "Evidence",
    "Decision",
    "Promotion",
)

RUN_STEPS = (
    "objective",
    "scope",
    "source_selection",
    "context_policy",
    "quality_gates",
    "committee_review",
    "evidence_export",
    "closeout_decision",
)

TRUTH_SOURCES = (
    "source",
    "tests",
    "schemas",
    "docs",
    "openspec",
    "claims",
    "evidence",
)

ADVISORY_PROJECTIONS = (
    ".ethos/state",
    "assistant-session-memory",
    "mcp-memory-adapter",
)

ALLOWED_DIFFERENCES = (
    "authority_binding",
    "profile_config",
    "adapter_binding",
    "strictness",
    "rollout",
)

COMMITTEE_ROLES = (
    {
        "id": "architecture-governance",
        "scope": "kernel, profile, authority, and workflow isomorphism",
    },
    {
        "id": "security-source-verification",
        "scope": "path containment, source verification, digest and HEAD binding",
    },
    {
        "id": "cli-mcp-api-contracts",
        "scope": "public command plane, MCP resources, and advisory API boundaries",
    },
    {
        "id": "retrieval-storage-eval",
        "scope": "local projection lifecycle, retrieval quality, and eval fixtures",
    },
)


@dataclass(frozen=True)
class GovernanceProfile:
    id: str
    mode: str
    subject: str
    capability_graph: tuple[str, ...] = CAPABILITY_GRAPH
    kernel_chain: tuple[str, ...] = KERNEL_CHAIN
    trust_lifecycle: tuple[str, ...] = TRUST_LIFECYCLE
    run_steps: tuple[str, ...] = RUN_STEPS
    truth_sources: tuple[str, ...] = TRUTH_SOURCES
    advisory_projections: tuple[str, ...] = ADVISORY_PROJECTIONS
    authority_binding: str = ""
    profile_config: tuple[str, ...] = ()
    adapter_binding: tuple[str, ...] = ()
    strictness: str = ""
    rollout: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "mode": self.mode,
            "subject": self.subject,
            "capability_graph": list(self.capability_graph),
            "kernel_chain": list(self.kernel_chain),
            "trust_lifecycle": list(self.trust_lifecycle),
            "run_steps": list(self.run_steps),
            "truth_sources": list(self.truth_sources),
            "advisory_projections": list(self.advisory_projections),
            "authority_binding": self.authority_binding,
            "profile_config": list(self.profile_config),
            "adapter_binding": list(self.adapter_binding),
            "strictness": self.strictness,
            "rollout": self.rollout,
        }


def canonical_governance_profiles() -> tuple[GovernanceProfile, ...]:
    return (
        GovernanceProfile(
            id="product-adopter",
            mode="product",
            subject="external repository",
            authority_binding="adopter repository truth plus ETHOS policy",
            profile_config=(
                "adopter root",
                "profile detection",
                "host surfaces",
                "domain gate mappings",
            ),
            adapter_binding=(
                "adopt profile",
                "fleet inspection",
                "shadow parity",
                "host projection",
            ),
            strictness="profile-selected governance gates with product schema floor",
            rollout="adopt, prove, report, land, publish under adopter branch policy",
        ),
        GovernanceProfile(
            id="self-governance",
            mode="self",
            subject="ETHOS repository",
            authority_binding="ETHOS repository truth and accepted decisions",
            profile_config=(
                "self root",
                "OpenSpec lifecycle depth",
                "self-hosting toolchain gates",
                "release readiness",
            ),
            adapter_binding=(
                "OpenSpec lifecycle",
                "claims",
                "Work Lane",
                "release readiness",
            ),
            strictness="product self-audit, lifecycle, release, and full proof gates",
            rollout="work lane, candidate, accepted root, local-only publication boundary",
        ),
    )


def governance_committee_profile() -> dict[str, Any]:
    return {
        "role_count": len(COMMITTEE_ROLES),
        "minimum_role_count": 4,
        "roles": [dict(role) for role in COMMITTEE_ROLES],
        "consensus_gate": {
            "required": True,
            "blocking_findings_must_be_resolved": True,
            "approval_scope": "all roles approve the same source-backed evidence package",
        },
    }


def governance_profile_report() -> dict[str, Any]:
    profiles = canonical_governance_profiles()
    by_id = {profile.id: profile.to_dict() for profile in profiles}
    reference = profiles[0]
    mismatches: list[str] = []
    for profile in profiles[1:]:
        for field in (
            "capability_graph",
            "kernel_chain",
            "trust_lifecycle",
            "run_steps",
            "truth_sources",
            "advisory_projections",
        ):
            if getattr(profile, field) != getattr(reference, field):
                mismatches.append(f"{profile.id}:{field}_mismatch")
    for profile in profiles:
        for field in ALLOWED_DIFFERENCES:
            value = getattr(profile, field)
            if not value:
                mismatches.append(f"{profile.id}:{field}_missing")
    committee = governance_committee_profile()
    if committee["role_count"] < committee["minimum_role_count"]:
        mismatches.append("campaign_committee_role_count_below_minimum")
    return {
        "ok": not mismatches,
        "isomorphic": not mismatches,
        "profiles": by_id,
        "shared_kernel": {
            "capability_graph": list(CAPABILITY_GRAPH),
            "kernel_chain": list(KERNEL_CHAIN),
            "trust_lifecycle": list(TRUST_LIFECYCLE),
            "run_steps": list(RUN_STEPS),
            "truth_sources": list(TRUTH_SOURCES),
            "advisory_projections": list(ADVISORY_PROJECTIONS),
        },
        "allowed_differences": list(ALLOWED_DIFFERENCES),
        "committee": committee,
        "required_gaps": mismatches,
    }
