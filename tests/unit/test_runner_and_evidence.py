from __future__ import annotations

from pathlib import Path

from ethos_adapters.runner import DryRunRunner, LocalSubprocessRunner
from ethos_core.action_graph import ActionNode
from ethos_repository.evidence import EvidenceSet, ProofRun, provenance_envelope, trim_output


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


def test_evidence_set_binds_head_and_digests() -> None:
    run = ProofRun(
        action_id="pytest",
        command=("pytest", "-q"),
        exit_code=0,
        stdout="22 passed",
        stderr="",
        state="passed",
    )

    evidence = EvidenceSet.from_runs(
        id="evidence:test",
        head="abc123",
        runs=(run,),
        durability="repository",
    )

    assert evidence.head == "abc123"
    assert evidence.digest
    assert evidence.runs[0].state == "passed"


def test_provenance_envelope_is_slsa_shaped() -> None:
    run = ProofRun(
        action_id="pytest",
        command=("pytest", "-q"),
        exit_code=0,
        stdout="22 passed",
        stderr="",
        state="passed",
    )
    evidence = EvidenceSet.from_runs(id="evidence:test", head="abc123", runs=(run,))

    envelope = provenance_envelope(evidence)

    assert envelope["predicateType"].endswith("/ethos-provenance/v1")
    assert envelope["subject"][0]["digest"]["sha256"] == evidence.digest
    assert envelope["predicate"]["head"] == "abc123"


def test_run_output_trimming_is_stable() -> None:
    trimmed = trim_output("x" * 50, limit=16)

    assert trimmed == "xxxxxxxxxxxxxxxx\n[trimmed 34 bytes]"
