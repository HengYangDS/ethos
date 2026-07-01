from __future__ import annotations

SAMPLE_REPOSITORIES = (
    "sample-basic-git",
    "sample-python-package",
    "sample-monorepo",
    "sample-gitlab",
    "sample-agentic",
    "sample-reference-adopter-profile",
)


def sample_repository_names() -> tuple[str, ...]:
    return SAMPLE_REPOSITORIES


def complete_governance_lifecycle() -> dict[str, object]:
    trust_envelope = {
        "claim_id": "sample-trust",
        "state": "active",
        "boundary": {"owner": "ethos-repository", "scope": "repository lifecycle"},
        "evidence": {
            "dated": "docs/evidence/sample.md",
            "digest_trusted": True,
            "commands": ["ethos prove --full --execute --json"],
        },
        "carriers": {"openspec": "openspec/changes/sample-change"},
        "fallback": "stop promotion and keep the previous repository contract",
        "kill_signal": "required lifecycle carrier missing",
        "promotion": {
            "targets": [
                {"kind": "source", "path": "packages/ethos/src/ethos/cli.py"},
                {"kind": "tests", "path": "tests/unit/test_cli_contracts.py"},
                {"kind": "openspec", "path": "openspec/specs/ethos-cli/spec.md"},
                {"kind": "evidence", "path": "docs/evidence/sample.md"},
            ],
            "ready": True,
        },
        "required_gaps": [],
    }
    capability_profile = {
        "family": "ethos-repository",
        "owner": {
            "package": "ethos-repository",
            "scope": "repository lifecycle governance",
        },
        "primary_invariant": "repository truth is promoted through claims and evidence",
        "routing_question": "Does this change alter repository trust admission?",
        "boundary_rules": [
            "OpenSpec records are specification carriers, not truth owners",
            "intake provider state remains projection evidence",
        ],
        "proof_profile": {
            "default_command": "ethos prove --json",
            "executed_command": "ethos prove --full --execute --json",
            "required_gates": ["claims", "schemas"],
        },
    }
    return {
        "trust_envelope": trust_envelope,
        "capability_profile": capability_profile,
        "openspec_lifecycle": {
            "change": "sample-change",
            "proposal": True,
            "design": True,
            "tasks": True,
            "delta_specs": True,
            "claim_binding": True,
        },
        "proof": {"executed": True, "state": "proven"},
        "required_gaps": [],
    }


def malformed_governance_lifecycle() -> dict[str, object]:
    return {
        "trust_envelope": {
            "claim_id": "sample-trust",
            "state": "active",
            "boundary": {"owner": "ethos-repository", "scope": "repository lifecycle"},
            "evidence": {
                "dated": "docs/evidence/missing.md",
                "digest_trusted": False,
                "commands": ["ethos prove --json"],
            },
            "carriers": {"openspec": "openspec/changes/sample-change"},
            "fallback": "stop promotion",
            "kill_signal": "required lifecycle carrier missing",
            "promotion": {
                "targets": [{"kind": "evidence", "path": "docs/evidence/missing.md"}],
                "ready": False,
            },
            "required_gaps": [
                "promotion_target_missing:docs/evidence/missing.md",
                "evidence.digest_untrusted",
            ],
        },
        "openspec_lifecycle": {
            "change": "sample-change",
            "proposal": True,
            "design": False,
            "tasks": True,
            "delta_specs": False,
            "claim_binding": False,
        },
        "proof": {"executed": False, "state": "ready"},
        "required_gaps": [
            "openspec_claim_binding_missing:sample-change",
            "promotion_target_missing:sample-trust:docs/evidence/missing.md",
            "executed_proof_missing",
            "malformed_openspec_carrier:sample-change",
        ],
    }


def reference_adopter_profile_fixture() -> dict[str, object]:
    return {
        "boundary": "adopter-profile-only",
        "profile_terms": ["raw/cache parity", "domain cache contract"],
        "core_product_terms": [],
        "evidence": {
            "kind": "shadow_parity_evidence",
            "capabilities": ["openspec-claims-trust-review", "work-lane-lifecycle"],
        },
    }
