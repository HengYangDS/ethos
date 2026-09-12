"""Real proof execution must describe the checkout and index actually checked."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC
from datetime import datetime
from pathlib import Path

import pytest

import ethos.adapters.mutation.proof as proof_owner
import ethos.surface.cli.root.proof as proof_cli
from ethos.adapters.mutation.proof import issue_proof_attestation
from ethos.adapters.mutation.proof import persist_proof_attestation
from ethos.adapters.mutation.proof import proof_gaps
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.contracts.plan import compile_plan
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import Commitment
from ethos.contracts.semantic import Facts
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import conformant_proof_check
from tests.support.governed_repository import current_proof_plan
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import issue_conformant_proof

_PROGRAM = """
from pathlib import Path
import os
import subprocess

mode = os.environ.get('ETHOS_SOURCE_PROBE', '')
source = Path('README.md')
marker = Path('build/ran')
marker.parent.mkdir(exist_ok=True)
marker.write_text('executed')
if mode == 'tracked':
    source.write_text('# different source\\n')
elif mode == 'deleted':
    source.unlink()
elif mode == 'index':
    original = source.read_bytes()
    source.write_text('# indexed only\\n')
    subprocess.run(['git', 'add', 'README.md'], check=True)
    source.write_bytes(original)
elif mode == 'policy':
    policy = Path('.ethos/profile.toml')
    policy.write_text(policy.read_text() + '\\n# changed during checks\\n')
elif mode == 'untracked':
    Path('new-source.py').write_text('changed = True\\n')
"""


@pytest.fixture
def proof_repository(tmp_path: Path) -> Path:
    """Declare actual native gates, with no mock proof or policy semantics."""
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    (repo / ".gitignore").write_text("build/\n")
    profile = repo / ".ethos/profile.toml"
    profile.write_text(
        profile.read_text()
        .replace(
            'command = ["sample", "test"]',
            "command = " + json.dumps([sys.executable, "-c", _PROGRAM]),
        )
        .replace(
            'command = ["sample", "typecheck"]',
            "command = " + json.dumps([sys.executable, "-c", "print('static green')"]),
        )
    )
    commit_fixture(repo, "declare real proof gates")
    return repo


@pytest.mark.parametrize("mode", ["tracked", "deleted", "index", "policy", "untracked"])
def test_public_proof_rejects_source_changes_during_successful_gates(
    proof_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    """A zero-exit gate cannot authorize another source or silently undo drift."""
    root = proof_repository
    head = git(root, "rev-parse", "HEAD")
    before = read_attestation_set(root)
    monkeypatch.setenv("ETHOS_SOURCE_PROBE", mode)

    completed = run_ethos_raw(
        "prove", "--full", "--execute", "--expect-head", head, "--json", cwd=root
    )
    payload = json.loads(completed.stdout)

    assert (root / "build/ran").read_text() == "executed"
    assert git(root, "rev-parse", "HEAD") == head
    assert git(root, "status", "--porcelain=v1")
    assert payload["verdict"] != "pass", payload
    assert "proof_execution_source" in json.dumps(payload)
    descriptor = payload["data"]["artifact_reference"]
    store = Path(git(root, "rev-parse", "--git-common-dir"))
    store = store if store.is_absolute() else root / store
    evidence = json.loads((store / "ethos" / descriptor["path"]).read_text())
    assert {check["action_id"] for check in evidence["checks"]} == {"sample-tests", "sample-static"}
    assert all(check["exit_code"] == 0 for check in evidence["checks"])
    assert read_attestation_set(root) == before


@pytest.mark.parametrize("kind", ["tracked", "index", "untracked"])
def test_dirty_source_is_refused_before_exact_commit_execution(
    proof_repository: Path,
    kind: str,
) -> None:
    """Exploratory content does not get silently attributed to the committed HEAD."""
    root = proof_repository
    head = git(root, "rev-parse", "HEAD")
    if kind == "untracked":
        (root / "new.py").write_text("value = 2\n")
    else:
        (root / "README.md").write_text("# dirty\n")
        if kind == "index":
            git(root, "add", "README.md")
    before = git(root, "status", "--porcelain=v1")
    completed = run_ethos_raw(
        "prove", "--full", "--execute", "--expect-head", head, "--json", cwd=root
    )
    payload = json.loads(completed.stdout)
    assert payload["verdict"] != "pass", payload
    assert not (root / "build/ran").exists()
    assert git(root, "status", "--porcelain=v1") == before


def test_clean_source_and_ignored_outputs_allow_exact_commit_proof(proof_repository: Path) -> None:
    """Output ownership, not blanket filesystem immutability, defines source scope."""
    root = proof_repository
    head = git(root, "rev-parse", "HEAD")
    completed = run_ethos_raw(
        "prove", "--full", "--execute", "--expect-head", head, "--json", cwd=root
    )
    payload = json.loads(completed.stdout)
    assert payload["verdict"] == "pass", payload
    assert completed.returncode == 0
    assert (root / "build/ran").is_file()
    assert not git(root, "status", "--porcelain=v1")
    assert payload["data"]["attestation"]["subject"] == f"git:commit:{head}"


@pytest.mark.parametrize("boundary", ["issuance", "selection"])
def test_direct_proof_boundary_rechecks_current_source(
    proof_repository: Path, boundary: str
) -> None:
    """SDK callers cannot evade source admission by avoiding the public CLI."""

    root = proof_repository
    head = git(root, "rev-parse", "HEAD")
    plan = current_proof_plan(root, expected_head=head)
    payload = {
        "plan": plan,
        "checks": tuple(
            conformant_proof_check(node.id, root, tree_ref=head) for node in plan.nodes
        ),
        "verdict": "pass",
        "issuer": "agent:test:source-binding",
        "scope": "repository",
        "boundary": "repository",
    }
    proof = issue_proof_attestation(root, payload) if boundary == "selection" else None
    before = read_attestation_set(root)
    (root / "README.md").write_text("# changed after planning\n")
    if proof is None:
        with pytest.raises(ValueError, match="proof_execution_source_changed"):
            issue_proof_attestation(root, payload)
    else:
        with pytest.raises(ValueError, match="proof_execution_source_changed"):
            persist_proof_attestation(root, proof)
    assert read_attestation_set(root) == before
    assert (root / "README.md").read_text() == "# changed after planning\n"


def test_historical_proof_without_source_binding_is_not_new_proof(proof_repository: Path) -> None:
    """Rehashing a plan without observed source cannot preserve its proof claim."""

    root = proof_repository
    head = git(root, "rev-parse", "HEAD")
    plan = current_proof_plan(root, expected_head=head)
    proof = issue_conformant_proof(root, head, plan=plan)
    values = dict(plan.facts["values"])
    del values["execution_source"]
    historical = compile_plan(
        Commitment.model_validate(dict(plan.commitment)) if plan.commitment else None,
        Facts.model_validate(plan.facts | {"observed_at": datetime.now(UTC), "values": values}),
        plan.nodes,
        policy=dict(plan.policy),
        prior_attestations=dict(plan.prior_attestations),
    )
    payload = proof.model_dump(mode="python", exclude={"id"})
    payload.update(
        facts_digest=historical.inputs.facts,
        plan_digest=historical.digest,
        effect_digest=historical.inputs.effect,
        payload={
            "kind": proof.payload.kind,
            "body": dict(proof.payload.body) | {"plan": historical.model_dump(mode="json")},
        },
    )
    old = Attestation.issue(payload)
    with pytest.raises(ValueError, match="proof_execution_source_binding_missing"):
        persist_proof_attestation(root, old)
    record_attestations(root, (old,))
    assert "proof_execution_source_binding_missing" in proof_gaps(root, head)
    assert read_attestation_set(root)[1] == (old,)


def test_unavailable_native_source_observation_cannot_issue_proof(
    proof_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Transport failure remains a precise source observation gap, not a traceback."""
    root = proof_repository
    head = git(root, "rev-parse", "HEAD")
    plan = current_proof_plan(root, expected_head=head)
    original = proof_owner.run_git

    def unavailable(directory, *args, **kwargs):
        if args[:2] == ("diff", "--cached"):
            raise subprocess.CalledProcessError(128, ["git", *args], stderr="index unreadable")
        return original(directory, *args, **kwargs)

    monkeypatch.setattr(proof_owner, "run_git", unavailable)
    with pytest.raises(ValueError, match="proof_execution_source_unavailable"):
        issue_conformant_proof(root, head, plan=plan)


def test_public_proof_preserves_source_drift_between_issuance_and_selection(
    proof_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late source drift emits one failed result, without selecting or retrying proof."""
    root = proof_repository
    head = git(root, "rev-parse", "HEAD")
    before = read_attestation_set(root)
    original = proof_cli.persist_proof_attestation
    attempts = []

    def drift(directory, proof):
        attempts.append(proof.id)
        (root / "README.md").write_text("# changed at selection\n")
        return original(directory, proof)

    monkeypatch.setattr(proof_cli, "persist_proof_attestation", drift)
    completed = run_ethos_raw(
        "prove", "--full", "--execute", "--expect-head", head, "--json", cwd=root
    )
    payload = json.loads(completed.stdout)
    assert payload["verdict"] == "block"
    assert "proof_execution_source_changed" in payload["required_gaps"]
    assert payload["data"]["artifact_reference"]["sha256"]
    assert len(attempts) == 1
    assert read_attestation_set(root) == before
    assert (root / "README.md").read_text() == "# changed at selection\n"
