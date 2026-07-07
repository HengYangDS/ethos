from __future__ import annotations

from pathlib import Path

import pytest

from ethos.adapters.gates.runner import DryRunRunner
from ethos.adapters.gates.runner import LocalSubprocessRunner
from ethos.repository.evidence.core import EvidenceSet
from ethos.repository.evidence.core import ProofRun
from ethos.repository.evidence.core import provenance_envelope
from ethos.repository.evidence.core import trim_output
from ethos_core.action_graph import ActionNode


def test_dry_run_runner_records_action_without_execution() -> None:
    node = ActionNode(id="status", kind="inspect", command=("ethos", "status", "--json"))

    result = DryRunRunner().run(node, root=Path.cwd())

    assert result.action_id == "status"
    assert result.state == "planned"
    assert result.exit_code is None


def test_local_runner_executes_successful_command(tmp_path: Path) -> None:
    node = ActionNode(id="python", kind="test", command=("python", "-c", "print('ok')"))

    result = LocalSubprocessRunner().run(node, root=tmp_path)

    assert result.state == "passed"
    assert result.exit_code == 0
    assert result.stdout.strip() == "ok"


def test_local_runner_treats_ethos_json_failure_as_failed(tmp_path: Path) -> None:
    node = ActionNode(
        id="ethos-json",
        kind="quality",
        command=(
            "python",
            "-c",
            (
                "import json; "
                "print(json.dumps({'ok': False, 'state': 'blocked', "
                "'required_gaps': ['sample_gap']}))"
            ),
        ),
    )

    result = LocalSubprocessRunner().run(node, root=tmp_path)

    assert result.exit_code == 0
    assert result.state == "failed"
    assert result.diagnostics == (
        {
            "kind": "ethos_result",
            "ok": False,
            "state": "blocked",
            "required_gaps": ["sample_gap"],
        },
    )


def test_local_runner_reports_missing_command_as_structured_failure(tmp_path: Path) -> None:
    node = ActionNode(
        id="missing-script",
        kind="quality",
        command=(".config/ci/scripts/missing.sh",),
    )

    result = LocalSubprocessRunner().run(node, root=tmp_path)

    assert result.action_id == "missing-script"
    assert result.state == "failed"
    assert result.exit_code == 127
    assert "missing.sh" in result.stderr
    assert result.diagnostics == (
        {
            "kind": "command_not_found",
            "missing": ".config/ci/scripts/missing.sh",
            "cwd": str(tmp_path),
            "required_gaps": ["missing_command:.config/ci/scripts/missing.sh"],
        },
    )


def test_evidence_set_binds_head_and_digests() -> None:
    run = ProofRun(
        action_id="pytest",
        command=("pytest", "-q"),
        exit_code=0,
        stdout="22 passed",
        stderr="",
        state="proven",
        verdict="passed",
        trust_bearing=True,
    )

    evidence = EvidenceSet.from_runs(
        id="evidence:test",
        head="abc123",
        runs=(run,),
        durability="repository",
    )

    assert evidence.head == "abc123"
    assert evidence.digest
    assert evidence.runs[0].state == "proven"


def test_provenance_envelope_is_slsa_shaped() -> None:
    run = ProofRun(
        action_id="pytest",
        command=("pytest", "-q"),
        exit_code=0,
        stdout="22 passed",
        stderr="",
        state="proven",
        verdict="passed",
        trust_bearing=True,
    )
    evidence = EvidenceSet.from_runs(id="evidence:test", head="abc123", runs=(run,))

    envelope = provenance_envelope(evidence)

    assert envelope["predicateType"].endswith("/ethos-provenance/v1")
    assert envelope["subject"][0]["digest"]["sha256"] == evidence.digest
    assert envelope["predicate"]["head"] == "abc123"


def test_run_output_trimming_is_stable() -> None:
    trimmed = trim_output("x" * 50, limit=16)

    assert trimmed == "xxxxxxxxxxxxxxxx\n[trimmed 34 bytes]"


def test_proof_run_rejects_schema_invalid_states() -> None:
    with pytest.raises(ValueError, match="invalid proof run state"):
        ProofRun(
            action_id="pytest",
            command=("pytest", "-q"),
            exit_code=0,
            stdout="",
            stderr="",
            state="passed",
        )


def test_accepted_risk_proof_run_requires_governance_reference() -> None:
    with pytest.raises(ValueError, match="requires governance_ref"):
        ProofRun(
            action_id="waiver",
            command=("ethos", "prove"),
            exit_code=0,
            stdout="",
            stderr="",
            state="accepted-risk",
        )


def test_proven_proof_run_must_be_trust_bearing() -> None:
    with pytest.raises(ValueError, match="proven proof run must be trust_bearing"):
        ProofRun(
            action_id="claim",
            command=("ethos", "quality", "claims", "--json"),
            exit_code=0,
            stdout="",
            stderr="",
            state="proven",
            verdict="passed",
            trust_bearing=False,
        )


def test_non_proven_proof_run_cannot_be_trust_bearing() -> None:
    with pytest.raises(ValueError, match="trust_bearing proof run must be proven"):
        ProofRun(
            action_id="claim",
            command=("ethos", "quality", "claims", "--json"),
            exit_code=None,
            stdout="",
            stderr="",
            state="planned",
            verdict="not_run",
            trust_bearing=True,
        )
