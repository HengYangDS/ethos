from __future__ import annotations

from ethos_core.contracts.context_projection import (
    context_retrieval_smoke_queries as _context_retrieval_smoke_queries,
)

SAMPLE_REPOSITORIES = (
    "sample-basic-git",
    "sample-python",
    "sample-monorepo",
    "sample-gitlab",
    "sample-agentic",
    "sample-reference-adopter-profile",
)


def context_retrieval_smoke_queries() -> tuple[dict[str, object], ...]:
    return _context_retrieval_smoke_queries()


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


def _rules_toml(*profiles: str) -> str:
    active = ", ".join(f'"{profile}"' for profile in profiles)
    return f"""[profiles]
active = [{active}]
"""


RULES_CONFORMANCE_PROFILES = {
    "generic": {
        "strict": False,
        "requires_openspec": False,
        "requires_hosted_ci": False,
        "requires_backlog": False,
        "requires_product_openspec_family": False,
        "paths": ["README.md"],
        "files": {".ethos/rules.toml": _rules_toml("generic")},
    },
    "python": {
        "strict": False,
        "requires_openspec": False,
        "requires_hosted_ci": False,
        "requires_backlog": False,
        "requires_product_openspec_family": False,
        "paths": ["packages/app/app.py"],
        "files": {
            ".ethos/rules.toml": _rules_toml("generic", "python")
            + """
[[rule]]
id = "adopter.python"
owner = "python-team"
authority_ref = "pyproject.toml"
contract_ref = "pyproject.toml"
subject = "source"
path_globs = ["**/*.py"]
severity = "advisory"
required_gates = []
stop_condition = "python_source_gap"
""".lstrip()
        },
    },
    "monorepo": {
        "strict": False,
        "requires_openspec": False,
        "requires_hosted_ci": False,
        "requires_backlog": False,
        "requires_product_openspec_family": False,
        "paths": ["packages/a/a.py"],
        "files": {".ethos/rules.toml": _rules_toml("generic", "python")},
    },
    "github": {
        "strict": False,
        "requires_openspec": False,
        "requires_hosted_ci": True,
        "requires_backlog": False,
        "requires_product_openspec_family": False,
        "paths": [".github/workflows/ethos.yml"],
        "files": {".ethos/rules.toml": _rules_toml("generic")},
    },
    "gitlab": {
        "strict": False,
        "requires_openspec": False,
        "requires_hosted_ci": True,
        "requires_backlog": False,
        "requires_product_openspec_family": False,
        "paths": [".gitlab-ci.yml"],
        "files": {".ethos/rules.toml": _rules_toml("generic")},
    },
    "legacy-v1": {
        "strict": False,
        "requires_openspec": False,
        "requires_hosted_ci": False,
        "requires_backlog": False,
        "requires_product_openspec_family": False,
        "paths": [".ethos/rules.toml"],
        "files": {".ethos/rules.toml": '[formats]\nuser_config = "TOML"\n'},
    },
    "custom": {
        "strict": False,
        "requires_openspec": False,
        "requires_hosted_ci": False,
        "requires_backlog": False,
        "requires_product_openspec_family": False,
        "paths": ["rules/custom/rules.toml"],
        "files": {".ethos/rules.toml": _rules_toml("generic")},
    },
    "reference-strict": {
        "strict": True,
        "requires_openspec": True,
        "requires_hosted_ci": False,
        "requires_backlog": False,
        "requires_product_openspec_family": False,
        "paths": ["rules/adopter/contracts.toml"],
        "files": {".ethos/rules.toml": _rules_toml("generic", "strict")},
    },
    "strict": {
        "strict": True,
        "requires_openspec": True,
        "requires_hosted_ci": False,
        "requires_backlog": False,
        "requires_product_openspec_family": False,
        "paths": ["rules/adopter/contracts.toml"],
        "files": {".ethos/rules.toml": _rules_toml("generic", "strict")},
    },
}

RULE_SHADOW_REPORT_FIXTURES = {
    "ethos": {
        "report": {
            "ok": True,
            "profile_stack": ["generic", "python"],
            "coverage_tier": "starter",
            "required_gap_kinds": [],
        },
        "stages": {
            "contracts-evaluator": "matched",
            "pep-no-side-effect": "matched",
            "strict-coverage": "starter-advisory",
        },
    },
    "reference-legacy": {
        "report": {
            "ok": False,
            "profile_stack": ["generic"],
            "coverage_tier": "starter",
            "required_gap_kinds": ["rule_schema_invalid"],
        },
        "stages": {
            "contracts-evaluator": "schema-migration-required",
            "pep-no-side-effect": "matched",
            "strict-coverage": "profile-opt-in-required",
        },
    },
    "sample-effect": {
        "report": {
            "ok": True,
            "profile_stack": ["generic"],
            "coverage_tier": "starter",
            "required_gap_kinds": [],
        },
        "stages": {
            "contracts-evaluator": "matched",
            "pep-no-side-effect": "matched",
            "strict-coverage": "starter-advisory",
        },
    },
}


def rules_conformance_profiles() -> dict[str, dict[str, object]]:
    return {name: dict(profile) for name, profile in RULES_CONFORMANCE_PROFILES.items()}


def normalized_rule_shadow_fixtures() -> dict[str, dict[str, object]]:
    return {name: dict(fixture) for name, fixture in RULE_SHADOW_REPORT_FIXTURES.items()}
