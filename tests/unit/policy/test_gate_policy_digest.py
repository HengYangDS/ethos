"""gate_policy_digest — cross-environment-stable policy identity and proof conformance.

A promotion proof binds not only to its own bytes but to WHAT the required gates ARE:
their canonical commands, trust classification, and script content. These tests pin the
audit's B10/B11/B12 behavior and the two forgery defenses (findings A/B):
  * B10: only the host interpreter path changes -> digest STABLE (proof stays valid).
  * B11: a gate's canonical command or classification changes -> digest CHANGES.
  * B12: a script-type gate's content is tampered (same path) -> digest CHANGES.
  * finding B: a covering run that did not run the real gate (/bin/true, or mislabeled
    trust/evidence) is rejected as not policy-conformant.
"""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

from ethos.adapters.mutation.proof import _promotion_required_gate_ids
from ethos.adapters.mutation.proof import _proof_path
from ethos.adapters.mutation.proof import gate_policy_gaps
from ethos.adapters.mutation.proof import record_executed_proof
from ethos.repository.evidence.core import EvidenceSet
from ethos.repository.policy.gates import Gate
from ethos.repository.policy.gates import canonical_gate_command
from ethos.repository.policy.gates import gate_policy_conformance_gaps
from ethos.repository.policy.gates import gate_policy_digest
from ethos.repository.policy.gates import gate_policy_fields
from ethos.repository.policy.gates import gate_registry
from ethos.repository.policy.gates import promotion_required_gate_ids
from tests.support.contract_helpers import conformant_proof_run

if TYPE_CHECKING:
    from pathlib import Path


def _conformant_runs(root: Path) -> list[dict[str, object]]:
    registry = gate_registry(root)
    runs: list[dict[str, object]] = []
    for gate_id in promotion_required_gate_ids(root):
        gate = registry.get(gate_id)
        if gate is None:
            continue
        runs.append(
            {
                "action_id": gate_id,
                "command": list(canonical_gate_command(gate.command)),
                "trust_bearing": gate.trust_bearing,
                "evidence_class": gate.evidence_class,
            }
        )
    return runs


def test_canonical_command_collapses_any_python_interpreter() -> None:
    # B10: different interpreter absolute paths canonicalize to the same command.
    a = canonical_gate_command(("/usr/bin/python3.12", "-m", "ethos.cli", "audit"))
    b = canonical_gate_command(("/opt/venv/bin/python3.13", "-m", "ethos.cli", "audit"))
    assert a == b
    assert a[0] == "python"


def test_canonical_command_keeps_scripts_and_entrypoints_verbatim() -> None:
    assert canonical_gate_command(("tools/ci/scripts/run-python-tests.sh",))[0] == (
        "tools/ci/scripts/run-python-tests.sh"
    )
    assert canonical_gate_command(("ethos", "quality", "claims"))[0] == "ethos"


def test_gate_policy_digest_is_deterministic(tmp_path: Path) -> None:
    assert gate_policy_digest(tmp_path) == gate_policy_digest(tmp_path)
    assert len(gate_policy_digest(tmp_path)) == 64


def test_gate_policy_source_digest_tracks_script_content(tmp_path: Path) -> None:
    # B12: a script gate's on-disk content is part of its policy identity.
    script_dir = tmp_path / "tools" / "ci" / "scripts"
    script_dir.mkdir(parents=True)
    script = script_dir / "run-python-tests.sh"
    script.write_text("#!/bin/sh\necho v1\n", encoding="utf-8")
    gate = Gate(id="x", kind="quality", command=("tools/ci/scripts/run-python-tests.sh",))

    first = gate_policy_fields(gate, tmp_path)["policy_source_digest"]
    script.write_text("#!/bin/sh\necho TAMPERED\n", encoding="utf-8")
    second = gate_policy_fields(gate, tmp_path)["policy_source_digest"]

    assert first != second
    assert first != ""


def test_gate_policy_source_digest_is_empty_for_in_process_gate(tmp_path: Path) -> None:
    gate = Gate(id="x", kind="quality", command=("python", "-m", "ethos.cli", "audit"))
    assert gate_policy_fields(gate, tmp_path)["policy_source_digest"] == ""


def test_conformant_runs_pass_policy_conformance(tmp_path: Path) -> None:
    assert gate_policy_conformance_gaps(_conformant_runs(tmp_path), tmp_path) == []


def test_forged_bin_true_run_is_not_policy_conformant(tmp_path: Path) -> None:
    # finding B: a covering run that never ran the real gate command is rejected.
    runs = _conformant_runs(tmp_path)
    runs[0]["command"] = ["/bin/true"]
    gaps = gate_policy_conformance_gaps(runs, tmp_path)
    assert any(g.startswith("proof_gate_not_policy_conformant:") for g in gaps)


def test_mislabeled_trust_bearing_run_is_not_policy_conformant(tmp_path: Path) -> None:
    runs = _conformant_runs(tmp_path)
    runs[0]["trust_bearing"] = not runs[0]["trust_bearing"]
    gaps = gate_policy_conformance_gaps(runs, tmp_path)
    assert any(g.startswith("proof_gate_not_policy_conformant:") for g in gaps)


def test_conformance_ignores_non_list_runs(tmp_path: Path) -> None:
    assert gate_policy_conformance_gaps("not-a-list", tmp_path) == []


def test_canonical_command_passes_through_empty() -> None:
    # gates.py:462 — an empty command has no interpreter to collapse.
    assert canonical_gate_command(()) == ()


def test_policy_source_digest_empty_for_empty_command(tmp_path: Path) -> None:
    # gates.py:480 — a gate with no command contributes no script digest.
    gate = Gate(id="x", kind="quality", command=())
    assert gate_policy_fields(gate, tmp_path)["policy_source_digest"] == ""


def test_conformance_skips_missing_run_and_non_dict_entries(tmp_path: Path) -> None:
    # gates.py:540->539 (a non-dict run entry is skipped when indexing by action_id) and
    # :550 (a required gate with NO covering run is the completeness check's concern, not
    # conformance). Drop the first required gate's run and inject a non-dict entry.
    runs: list[object] = ["not-a-dict", *_conformant_runs(tmp_path)[1:]]
    assert gate_policy_conformance_gaps(runs, tmp_path) == []


def test_conformance_skips_required_gate_absent_from_registry(tmp_path: Path) -> None:
    # gates.py:547 — an adopter's declared native gate is in the required set but NOT in
    # the product registry (gate is None); conformance can only judge registry gates.
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "profile.toml").write_text(
        'profile_id = "acme"\n[proof]\ncode_correctness_gates = ["acme-tests"]\n',
        encoding="utf-8",
    )
    assert "acme-tests" in promotion_required_gate_ids(tmp_path)
    assert "acme-tests" not in gate_registry()
    # No runs at all: every gate is either absent-from-registry (547) or run-absent (550).
    assert gate_policy_conformance_gaps([], tmp_path) == []


def test_adopter_gate_descriptor_participates_in_policy_conformance(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos/profile.toml").write_text(
        """profile_id = "acme"
[proof]
code_correctness_gates = ["acme-tests"]
[[proof.gates]]
id = "acme-tests"
kind = "quality"
command = ["uv", "run", "pytest"]
evidence_class = "proof"
trust_bearing = true
""",
        encoding="utf-8",
    )
    runs = _conformant_runs(tmp_path)
    adopter_run = next(run for run in runs if run["action_id"] == "acme-tests")
    adopter_run["command"] = ["/bin/true"]

    assert gate_policy_conformance_gaps(runs, tmp_path) == [
        "proof_gate_not_policy_conformant:acme-tests"
    ]


def test_gate_policy_gaps_absent_record_is_empty(tmp_path: Path) -> None:
    # proof.py:187 — no proof record at head -> gate_policy_gaps reports nothing
    # (absence is the caller's proof_not_proven concern).
    assert gate_policy_gaps(tmp_path, "f" * 40) == []


def test_gate_policy_gaps_flags_stale_digest(tmp_path: Path) -> None:
    # proof.py:191 — a recorded proof whose stored gate_policy_digest no longer matches
    # the live one is stale (a gate's policy changed since the proof was recorded).
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
    head = "a" * 40
    runs = tuple(conformant_proof_run(g, tmp_path) for g in _promotion_required_gate_ids(tmp_path))
    record_executed_proof(
        tmp_path, EvidenceSet.from_runs(id="proof", head=head, runs=runs).to_dict()
    )
    # Corrupt the stored digest on disk so it no longer matches the live one.
    path = _proof_path(tmp_path, head)
    record = json.loads(path.read_text(encoding="utf-8"))
    record["gate_policy_digest"] = "stale-digest"
    path.write_text(json.dumps(record), encoding="utf-8")

    assert "proof_policy_digest_stale" in gate_policy_gaps(tmp_path, head)
