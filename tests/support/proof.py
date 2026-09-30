"""Construct policy-bound native checks, proof plans and isolated evidence."""

from __future__ import annotations

import os
import sys
import tomllib
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import tomli_w

from ethos.adapters.admission.current.resolution import resolve_current_resolution
from ethos.adapters.mutation.proof import issue_proof_attestation
from ethos.adapters.mutation.proof import persist_proof_attestation
from ethos.adapters.mutation.proof import proof_attestation
from ethos.adapters.mutation.proof import proof_gaps
from ethos.adapters.mutation.proof import proof_plan
from ethos.adapters.mutation.proof_artifacts import proof_artifact_root
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.workspace import workspace_status_observation
from ethos.contracts.gates import Gate
from ethos.contracts.gates import GateProofSets
from ethos.contracts.gates import GateRegistryDeclaration
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_active_commitment
from tests.support.governed_repository import write_test_profile

if TYPE_CHECKING:
    from ethos.contracts.plan import TransitionPlan
    from ethos.contracts.semantic import Attestation


def declare_quality_fixture(
    root: Path,
    *,
    provider: str = "code_quality",
    gates: tuple[Gate, ...] | None = None,
    registry: bool = False,
    behavior_command: tuple[str, ...] = (),
    static_command: tuple[str, ...] = (),
) -> None:
    """Declare a native quality fixture through the same strict models as its consumers."""
    selected = gates or tuple(
        Gate(
            id=axis,
            kind=kind,
            command=command,
            providers=() if command else (f"ethos.adapters.gates.{provider}:{report}_report",),
            verification_providers=(f"ethos.adapters.gates.{provider}:{report}_report",)
            if command
            else (),
            profile="repository",
            execution_mode="provider",
            tool_adapter="ethos",
        )
        for axis, kind, report, command in (
            ("behavior", "test", "behavior", behavior_command),
            ("static", "lint", "static", static_command),
        )
    )
    names = tuple(gate.id for gate in selected)
    if registry:
        path = root / "system/gates.toml"
        path.parent.mkdir(exist_ok=True)
        declaration = GateRegistryDeclaration(
            id="native-quality",
            proof_sets=GateProofSets(default=names, full=names),
            gates=selected,
        )
        path.write_text(tomli_w.dumps(declaration.model_dump(mode="json", exclude_none=True)))
        proof = {"gate_registry": "system/gates.toml"}
    else:
        proof = {
            "code_correctness_gates": names,
            "gates": selected,
            "code_correctness_map": {"behavior": names[0], "static-analysis": names[-1]},
        }
    write_test_profile(root, proof=proof)


def python_quality_files(*, defect: str = "none") -> dict[str, str]:
    """Return fresh locked Python inputs, shared by native adoption workload fixtures."""
    source = Path(__file__).resolve().parents[1] / "fixtures/quality-sample"
    files = {
        "pyproject.toml": (source / "pyproject.toml").read_text(),
        "uv.lock": (source / "uv.lock").read_text(),
        ".gitignore": ".venv/\n__pycache__/\n",
        "src/sample/__init__.py": "def answer() -> int:\n    return 42\n",
        "tests/test_sample.py": (
            "from sample import answer\n\n\ndef test_answer() -> None:\n    assert answer() == 42\n"
        ),
    }
    match defect:
        case "none" | "plugin-disabled":
            pass
        case "strict-config":
            files["pytest.toml"] = (
                '[pytest]\naddopts = ["--strict-config"]\ncache_dir = ".cache/pytest"\n'
            )
        case "wrong-result":
            files["src/sample/__init__.py"] = files["src/sample/__init__.py"].replace("42", "41")
        case "lint-error":
            files["src/sample/__init__.py"] = "import os\n\n" + files["src/sample/__init__.py"]
        case "unused-source":
            files["src/sample/unused.py"] = "def never_called() -> int:\n    return 0\n"
        case "all-skipped":
            files["tests/test_sample.py"] = (
                "import pytest\n\nfrom sample import answer\n\n\n"
                "@pytest.mark.skip(reason='not executed')\n"
                + files["tests/test_sample.py"].split("\n\n\n", 1)[1]
            )
        case "missing-lock":
            files.pop("uv.lock")
        case "lock-drift":
            files["pyproject.toml"] = files["pyproject.toml"].replace(
                '"pytest-cov>=7.1.0"]', '"pytest-cov>=7.1.0", "pytest-timeout>=2.4.0"]'
            )
        case _:
            message = f"unknown Python quality defect: {defect}"
            raise ValueError(message)
    return files


def go_quality_files(
    overrides: dict[str, str] | None = None, *, go_version: str = "1.26"
) -> dict[str, str]:
    """Return fresh native Go inputs while leaving each counterexample explicit."""
    return {
        "go.mod": f"module example.invalid/quality\n\ngo {go_version}\n",
        "answer.go": "package quality\nfunc Answer() int { return 42 }\n",
        "answer_test.go": 'package quality\nimport "testing"\n'
        'func TestAnswer(t *testing.T) { if Answer() != 42 { t.Fatal("wrong") } }\n',
        **(overrides or {}),
    }


def issue_conformant_proof(
    repo,
    head,
    *,
    plan=None,
    checks=None,
    full=False,
    issuer="agent:test:fixture:proof",
    issued_at=datetime(2026, 7, 26, tzinfo=UTC),
    boundary="repository",
):
    """Issue one proof Attestation from the repository's exact declared policy."""
    plan = plan or current_proof_plan(repo, expected_head=head, full=full)
    if checks is None:
        checks = conformant_proof_checks(plan)
    return issue_proof_attestation(
        repo,
        {
            "plan": plan,
            "checks": checks,
            "verdict": "pass",
            "issuer": issuer,
            "issued_at": issued_at,
            "scope": "repository",
            "boundary": boundary,
        },
    )


def current_proof_plan(
    repo: Path,
    *,
    expected_head: str,
    gate_ids: tuple[str, ...] = (),
    full: bool = False,
):
    """Compile proof from the production resolution of one exact current HEAD."""
    observed_head = git(repo, "rev-parse", "HEAD")
    if observed_head != expected_head:
        msg = f"fixture_proof_head_not_current:{expected_head}:{observed_head}"
        raise AssertionError(msg)
    status, authority = workspace_status_observation(
        repo,
        include_foreign_path_scope=False,
    )
    resolution = resolve_current_resolution(
        repo,
        status=status,
        authority=authority,
        changed=True,
    )
    if resolution.verdict != "pass":
        msg = "fixture_current_resolution_not_passed:" + ",".join(resolution.required_gaps)
        raise AssertionError(msg)
    return proof_plan(
        repo,
        resolution=resolution,
        gate_ids=gate_ids,
        full=full,
    )


def seed_executed_proof(repo: Path, head: str, *, full: bool = False) -> None:
    """Persist one complete policy-conformant generic proof Attestation."""
    branch = git(repo, "branch", "--show-current")
    holder = str(leases_by_branch(repo).get(branch, {}).get("holder_ref") or "")
    original = os.environ.get("ETHOS_ACTOR")
    if holder:
        os.environ["ETHOS_ACTOR"] = holder
    try:
        persist_proof_attestation(
            repo,
            issue_conformant_proof(
                repo,
                head,
                full=full,
                issued_at=datetime.now(UTC),
            ),
        )
    finally:
        if original is None:
            os.environ.pop("ETHOS_ACTOR", None)
        else:
            os.environ["ETHOS_ACTOR"] = original


def conformant_proof_checks(plan: TransitionPlan) -> tuple[dict[str, object], ...]:
    """Project synthetic checks from the plan; issuance independently admits its policy."""
    gates = {gate["id"]: gate for gate in plan.policy["gates"]}
    return tuple(
        {
            "action_id": node.id,
            "command": list(node.command),
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "verdict": "pass",
            "evidence_class": gates[node.id]["evidence_class"],
            "trust_bearing": gates[node.id]["trust_bearing"],
            "diagnostics": [],
        }
        for node in plan.nodes
    )


def proof_repository(path: Path) -> tuple[Path, str]:
    repo = init_git_repo(path)
    adopt_and_commit(repo)
    write_active_commitment(repo, change_id="proof-binding")
    return repo, commit_fixture(repo, "bind proof")


def store_proof(root: Path, record: Attestation, *, selected: bool = True) -> None:
    store = proof_artifact_root(root)
    store.mkdir(parents=True, exist_ok=True)
    (store / f"{record.id}.json").write_text(record.canonical_json(), encoding="utf-8")
    if selected:
        record_attestations(root, (record,))


def assert_selected_proof(
    root: Path, head: str, *, selected: Attestation | None = None, gap: str | None = None
) -> None:
    assert proof_attestation(root, head) == selected
    assert proof_gaps(root, head) == ([] if gap is None else [gap])


def declare_native_proof_checks(root: Path, *, test: str, typecheck: str) -> None:
    """Replace the selected fixture registry with executable source observations."""
    profile = tomllib.loads((root / ".ethos/profile.toml").read_text())
    binding = profile.get("proof", {}).get("gate_registry")
    if not isinstance(binding, str) or not binding:
        message = "fixture_native_gate_registry_missing"
        raise ValueError(message)
    registry = root / binding
    if not registry.is_file():
        message = "fixture_native_gate_registry_unavailable"
        raise ValueError(message)
    ids = ["sample-tests", "sample-static"]
    gates = []
    for name, program, dimension, writes in (
        (ids[0], test, "source-observation", True),
        (ids[1], typecheck, "policy-observation", False),
    ):
        gate = {
            "id": name,
            "kind": "governance",
            "command": [sys.executable, "-c", program],
            "profile": "repository",
            "toolchain": "python",
            "asset_classes": ["fixture-source"],
            "dimensions": [dimension],
            "execution_mode": "subprocess",
            "evidence_class": "contract",
            "trust_bearing": True,
            "tool_adapter": "repository-native",
            "writes_files": writes,
        }
        if writes:
            gate["resource_locks"] = {"*": "exclusive"}
        gates.append(gate)
    registry.write_text(
        tomli_w.dumps(
            {
                "schema_version": 1,
                "id": "fixture-native-checks",
                "proof_sets": {"default": ids, "full": ids},
                "gates": gates,
            }
        ),
        encoding="utf-8",
    )
