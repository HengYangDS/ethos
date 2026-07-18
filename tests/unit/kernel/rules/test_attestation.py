from __future__ import annotations

from pathlib import Path

from ethos.repository.policy.rules.evaluation import rules_evaluation_report
from ethos_core.contracts.rules import RuleAttestation
from ethos_core.contracts.rules import rule_attestation_gaps


def test_rule_attestation_verifier_detects_tampering() -> None:
    evaluation = rules_evaluation_report(Path(), phase="plan", head="abc123")
    attestation = RuleAttestation(
        head=str(evaluation["head"]),
        evaluation_digest=str(evaluation["digest"]),
        rule_set_digest=str(evaluation["rule_set_digest"]),
        compiled_policy_digest=str(evaluation["compiled_policy_digest"]),
        fact_snapshot_digest=str(evaluation["fact_snapshot_digest"]),
        actor="local",
        scope="repository",
        runner_identity="ethos",
        input=dict(evaluation["input_snapshot"]),
        output={
            "state": evaluation["state"],
            "required_gaps": evaluation["required_gaps"],
            "required_gates": evaluation["required_gates"],
        },
    ).to_dict()

    assert rule_attestation_gaps(attestation, evaluation) == ()

    tampered = {**attestation, "evaluation_digest": "0" * 64, "head": "stale"}

    assert rule_attestation_gaps(tampered, evaluation) == (
        "rule_attestation_mismatch:head",
        "rule_attestation_mismatch:evaluation_digest",
    )

    tampered_input = {
        **attestation,
        "input": {**dict(attestation["input"]), "phase": "publish"},
    }
    assert "rule_attestation_mismatch:input_digest" in rule_attestation_gaps(
        tampered_input,
        evaluation,
    )

    tampered_output = {
        **attestation,
        "output": {
            **dict(attestation["output"]),
            "required_gaps": ["hidden"],
        },
    }
    assert "rule_attestation_mismatch:output_required_gaps" in rule_attestation_gaps(
        tampered_output,
        evaluation,
    )
