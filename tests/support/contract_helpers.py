"""Shared fixtures for the CLI contract test suites.

The contract coverage lives across sibling `test_contracts*.py` modules split by
command family; these helpers (git plumbing, sample-repo scaffolding, adopt/proof
seeding) are the cross-cutting setup every split imports.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from ethos.adapters.mutation.proof import _promotion_required_gate_ids
from ethos.repository.adoption.planner import adoption_plan

if TYPE_CHECKING:
    from pathlib import Path


def git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip()


def init_git_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    git(path, "init", "-b", "dev")
    git(path, "config", "commit.gpgsign", "false")
    (path / ".gitignore").write_text(".ethos/state/*\n!.ethos/state/.gitignore\n", encoding="utf-8")
    (path / "README.md").write_text("# sample\n", encoding="utf-8")
    (path / ".ethos" / "state").mkdir(parents=True)
    (path / ".ethos" / "state" / ".gitignore").write_text("*\n!.gitignore\n", encoding="utf-8")
    git(path, "add", ".")
    git(
        path,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "init",
    )
    return path


def adopt_and_commit(repo: Path) -> None:
    plan = adoption_plan(repo, profile="generic", apply=True)
    assert plan["applied"] is True
    _declare_minimal_code_correctness(repo)
    git(repo, "add", ".")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "adopt ethos governance",
    )


def _declare_minimal_code_correctness(repo: Path) -> None:
    """Declare a minimal, axis-covering code-correctness map on the scaffolded profile.

    `ethos adopt` scaffolds a recognized adopter profile but deliberately leaves the
    code-correctness declaration commented out — an adopter's real test/lint commands are
    toolchain-specific and cannot be guessed. The honest onboarding lifecycle is therefore
    adopt -> DECLARE your native code-correctness gates -> prove. These fixtures walk that
    third step: they append two qualifying native gates (one behavior, one static-analysis)
    and map the required axes, so a proof seeded over the required floor is also complete
    on the code-correctness dimension (Tier 1.2)."""
    profile_path = repo / ".ethos" / "profile.toml"
    profile_path.write_text(
        profile_path.read_text(encoding="utf-8")
        + "\n"
        + "[proof]\n"
        + 'code_correctness_gates = ["sample-tests", "sample-static"]\n\n'
        + "[proof.code_correctness_map]\n"
        + 'behavior = "sample-tests"\n'
        + 'static-analysis = "sample-static"\n\n'
        + "[[proof.gates]]\n"
        + 'id = "sample-tests"\n'
        + 'kind = "test"\n'
        + 'command = ["sample", "test"]\n'
        + 'dimensions = ["test", "coverage"]\n'
        + 'execution_mode = "subprocess"\n'
        + 'evidence_class = "proof"\n'
        + "trust_bearing = true\n"
        + 'tool_adapter = "repository-native"\n\n'
        + "[[proof.gates]]\n"
        + 'id = "sample-static"\n'
        + 'kind = "typing"\n'
        + 'command = ["sample", "typecheck"]\n'
        + 'dimensions = ["static-analysis"]\n'
        + 'execution_mode = "subprocess"\n'
        + 'evidence_class = "contract"\n'
        + "trust_bearing = true\n"
        + 'tool_adapter = "repository-native"\n',
        encoding="utf-8",
    )


def seed_executed_proof(repo: Path, head: str) -> None:
    """Record an executed-proof at HEAD, as `ethos prove --execute` would.

    Land/publish now require a HEAD-keyed proof record before the merge, so tests
    exercising land mechanics seed the proof the same way the prove command does. The
    record is self-authenticating (digest recomputed on read), so this seeds a REAL
    evidence body — a proof cannot be faked, in tests or production.
    """
    from ethos.adapters.mutation.proof import record_executed_proof
    from ethos.repository.evidence.core import EvidenceSet

    # Seed a COMPLETE, POLICY-CONFORMANT promotion proof (one passing run per required
    # gate id, carrying that gate's canonical command / trust_bearing / evidence_class):
    # land/publish require the proof to cover the required floor AND each run to conform
    # to its gate's live policy identity, so a placeholder command no longer suffices.
    runs = tuple(
        conformant_proof_run(gate_id, repo) for gate_id in _promotion_required_gate_ids(repo)
    )
    record_executed_proof(repo, EvidenceSet.from_runs(id="proof", head=head, runs=runs).to_dict())


def conformant_proof_run(gate_id: str, root: Path) -> object:
    """Build a ProofRun that conforms to `gate_id`'s live policy identity.

    Mirrors what `ethos prove --execute` records: the gate's canonical command and its
    declared trust_bearing / evidence_class, so the run passes gate_policy_conformance.
    Gate ids absent from the product registry (e.g. an adopter's declared native gates)
    fall back to a trust-bearing test run — conformance only checks registry gates.
    """
    from ethos.repository.evidence.core import ProofRun
    from ethos.repository.policy.gates import canonical_gate_command
    from ethos.repository.policy.gates import gate_registry

    gate = gate_registry(root).get(gate_id)
    if gate is None:
        command: tuple[str, ...] = ("pytest",)
        trust_bearing = True
        evidence_class = "test"
    else:
        command = canonical_gate_command(gate.command)
        trust_bearing = gate.trust_bearing
        evidence_class = gate.evidence_class
    # ProofRun enforces trust_bearing <=> state == "proven"; a non-trust-bearing gate's
    # passing run is "executed", not "proven".
    state = "proven" if trust_bearing else "executed"
    return ProofRun(
        action_id=gate_id,
        command=command,
        exit_code=0,
        stdout="",
        stderr="",
        state=state,
        evidence_class=evidence_class,
        verdict="passed",
        trust_bearing=trust_bearing,
        diagnostics=(),
    )
