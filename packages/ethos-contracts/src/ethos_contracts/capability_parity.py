from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class CapabilityParityRecord:
    capability: str
    source_location: str
    target_home: str
    disposition: str
    required_tests: tuple[str, ...]
    parity_criterion: str
    rollback_impact: str


CAPABILITY_PARITY_LEDGER = (
    CapabilityParityRecord(
        capability="work-lane-lifecycle",
        source_location="alphasim-dmgr packages/ethos-git worktree lifecycle modules",
        target_home="ethos-repository + ethos-adapters + ethos-test",
        disposition="migrate-to-product",
        required_tests=(
            "status/lane/prewrite golden JSON",
            "start lease and execution registry",
            "handoff and closeout dry-run/apply admission",
            "candidate lock and stale-base rejection",
            "foreign lane observe-only protection",
        ),
        parity_criterion=(
            "same lane role, lease, handoff, candidate, closeout, repair, and cleanup verdicts"
        ),
        rollback_impact=(
            "embedded dmgr lifecycle remains frozen fallback until shadow parity passes"
        ),
    ),
    CapabilityParityRecord(
        capability="proof-evidence-chronicle",
        source_location="alphasim-dmgr ethos-proof and tools/quality proof kernel",
        target_home="ethos-repository + ethos-contracts + ethos-test",
        disposition="migrate-to-product",
        required_tests=(
            "proof JSON schema and golden output",
            "HEAD and digest binding",
            "required/advisory gap classification",
            "host-local non-claim boundary",
        ),
        parity_criterion=(
            "same objective resolution, evidence digest, HEAD binding, and required gaps"
        ),
        rollback_impact="embedded proof remains comparison oracle during rollout",
    ),
    CapabilityParityRecord(
        capability="campaign-hypothesis-evolution",
        source_location="alphasim-dmgr ethos-campaign mission and hypothesis modules",
        target_home="ethos-repository + ethos-core",
        disposition="migrate-to-product",
        required_tests=(
            "campaign start/iterate/feedback/select/challenge/close fixtures",
            "hypothesis exhaustion challenge",
            "closeout evidence digest",
        ),
        parity_criterion=(
            "same opportunity, hypothesis, challenge, proof, and closeout lifecycle states"
        ),
        rollback_impact="embedded campaign remains reference for long-running dmgr work",
    ),
    CapabilityParityRecord(
        capability="assistant-playbooks-skills",
        source_location=(
            "alphasim-dmgr .agents/skills and ethos-assistants activation/surface modules"
        ),
        target_home="ethos-assistants + ethos-contracts + ethos-adapters",
        disposition="split",
        required_tests=(
            "activation policy schema fixtures",
            "changed-scope routing and coactivation",
            "pre-read and post-check validation",
            "projection drift and unregistered surface checks",
        ),
        parity_criterion=(
            "same playbook routing, projection classification, and external method-pack boundary"
        ),
        rollback_impact="repo-local skill content stays adopter projection, not product truth",
    ),
    CapabilityParityRecord(
        capability="quality-determinism-local-state",
        source_location="alphasim-dmgr tools/quality gates and local-state config",
        target_home="ethos-repository + ethos-contracts + ethos-adapters",
        disposition="migrate-to-product",
        required_tests=(
            "artifact path catalog",
            "stable JSON ordering",
            "local-state physical policy",
            "stale artifact detection",
            "retired command surface scan",
        ),
        parity_criterion=(
            "same deterministic artifact, command surface, local state, "
            "and evidence freshness verdicts"
        ),
        rollback_impact="dmgr raw/cache/SQL/DQC gates remain adopter profile mappings",
    ),
    CapabilityParityRecord(
        capability="openspec-claims-trust-review",
        source_location="alphasim-dmgr ethos-spec admission and OpenSpec modules",
        target_home="ethos-contracts + ethos-repository + ethos-adapters",
        disposition="migrate-to-product",
        required_tests=(
            "valid and invalid claim TOML fixtures",
            "terminal evidence stale digest rejection",
            "OpenSpec active change claim binding",
            "capability family coverage",
        ),
        parity_criterion=(
            "same claim lifecycle, official OpenSpec validation, trust review, and evidence refs"
        ),
        rollback_impact="embedded claim/OpenSpec mechanisms remain migration oracle",
    ),
    CapabilityParityRecord(
        capability="dmgr-domain-contract-profile",
        source_location="alphasim-dmgr rules/dmgr and profile adapters",
        target_home="adopter profile only",
        disposition="adopter-domain-only",
        required_tests=(
            "dmgr profile gate mapping fixtures",
            "raw/cache/conf/alphasim terms forbidden in product core",
            "external ETHOS shadow plan against dmgr",
        ),
        parity_criterion=(
            "generic ETHOS plans dmgr gates through profile without hardcoding domain semantics"
        ),
        rollback_impact=(
            "domain-specific embedded checks remain fallback until external profile proves parity"
        ),
    ),
)


def capability_parity_records() -> list[dict[str, object]]:
    return [asdict(record) for record in CAPABILITY_PARITY_LEDGER]
