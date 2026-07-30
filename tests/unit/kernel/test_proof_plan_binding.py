from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.proof as proof_module
from ethos.adapters.mutation.proof import attestation_store_dir
from ethos.adapters.mutation.proof import issue_proof_attestation
from ethos.adapters.mutation.proof import persist_proof_attestation
from ethos.adapters.mutation.proof import proof_attestation
from ethos.adapters.mutation.proof import proof_gaps
from ethos.adapters.mutation.proof import proof_plan
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.contracts.semantic import Attestation
from ethos.repository.adoption.planner import adoption_plan
from ethos.repository.policy.gates import canonical_gate_command
from ethos.repository.policy.gates import resolve_gate_policy
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


def _commit(root: Path, message: str) -> str:
    git(root, "add", ".")
    git(
        root,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        message,
    )
    return git(root, "rev-parse", "HEAD")


def _write_script_gate_policy(root: Path) -> None:
    profile = root / ".ethos" / "profile.toml"
    profile.parent.mkdir(parents=True, exist_ok=True)
    profile.write_text(
        'profile_id = "policy-test"\n\n[proof]\ngate_registry = "system/gates.toml"\n',
        encoding="utf-8",
    )
    registry = root / "system" / "gates.toml"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(
        'schema_version = 1\nid = "policy-test"\n\n'
        '[proof_sets]\ndefault = ["publish"]\nfull = ["publish"]\n\n'
        '[[gates]]\nid = "publish"\nregistries = ["runtime"]\n'
        'kind = "release"\ncommand = ["publish"]\ndepends_on = ["check"]\n\n'
        '[[gates]]\nid = "check"\nregistries = ["runtime"]\n'
        'kind = "test"\ncommand = ["tools/check.sh"]\n'
        'dimensions = ["behavior"]\nevidence_class = "proof"\ntrust_bearing = true\n',
        encoding="utf-8",
    )
    script = root / "tools" / "check.sh"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")


def _write_commitment(root: Path) -> None:
    carrier = root / "openspec" / "changes" / "proof-binding"
    carrier.mkdir(parents=True)
    (carrier / "commitment.toml").write_text(
        """schema_version = 1
id = "change:proof-binding"
intent = "Bind proof to the governed change."
subjects = ["repository:self"]
scope = ["**"]
permissions = ["repository.read"]
""",
        encoding="utf-8",
    )


def _adopted_repo(path: Path) -> tuple[Path, str]:
    repo = init_git_repo(path)
    adoption_plan(repo, apply=True)
    profile = repo / ".ethos" / "profile.toml"
    profile.write_text(
        profile.read_text(encoding="utf-8")
        + """
[openspec]
material_paths = ["openspec/**"]

[proof]
required_gates = ["sample-tests", "sample-static"]

[proof.code_axes]
behavior = "sample-tests"
static-analysis = "sample-static"

[[proof.gates]]
id = "sample-tests"
kind = "test"
command = ["sample", "test"]
dimensions = ["test", "coverage"]
execution_mode = "subprocess"
evidence_class = "proof"
trust_bearing = true
tool_adapter = "repository-native"

[[proof.gates]]
id = "sample-static"
kind = "typing"
command = ["sample", "typecheck"]
dimensions = ["static-analysis"]
execution_mode = "subprocess"
evidence_class = "contract"
trust_bearing = true
tool_adapter = "repository-native"
""",
        encoding="utf-8",
    )
    commitment = repo / ".ethos" / "commitment.toml"
    commitment.write_text(
        """schema_version = 1
id = "repository:repo"
intent = "Govern this adopted repository."
subjects = ["repository:repo"]
scope = ["**"]
permissions = ["repository.read", "git.ref.compare-and-swap"]
""",
        encoding="utf-8",
    )
    _write_commitment(repo)
    return repo, _commit(repo, "adopt and bind proof")


def _proof_checks(root: Path) -> tuple[dict[str, object], ...]:
    policy = resolve_gate_policy(root)
    registry = policy.registry
    checks: list[dict[str, object]] = []
    for gate_id in policy.gate_ids:
        gate = registry.get(gate_id)
        checks.append(
            {
                "action_id": gate_id,
                "command": list(canonical_gate_command(gate.command)) if gate else ["pytest"],
                "exit_code": 0,
                "stdout": f"{gate_id} passed",
                "stderr": "",
                "verdict": "pass",
                "evidence_class": gate.evidence_class if gate else "test",
                "trust_bearing": gate.trust_bearing if gate else True,
                "diagnostics": [],
            }
        )
    return tuple(checks)


def _proof_attestation(root: Path, head: str) -> Attestation:
    plan = proof_plan(root, head=head)
    return issue_proof_attestation(
        root,
        {
            "plan": plan,
            "checks": _proof_checks(root),
            "verdict": "pass",
            "issuer": "agent:test:case:proof",
            "issued_at": datetime(2026, 7, 26, tzinfo=UTC),
            "scope": "repository",
            "boundary": "repository",
        },
    )


def test_proof_plan_binds_commitment_facts_and_gate_policy(tmp_path: Path) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")

    plan = proof_plan(repo, head=head)

    assert plan.commitment_digest
    assert plan.facts_digest
    assert plan.policy_digest
    assert plan.to_dict()["inputs"] == {
        "commitment": plan.commitment_digest,
        "facts": plan.facts_digest,
        "policy": plan.policy_digest,
    }
    assert plan.facts["values"]["change_id"] == "proof-binding"
    assert plan.permissions == ("repository.read",)


def test_proof_plan_has_no_digest_override_escape_hatch(tmp_path: Path) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")

    with pytest.raises(TypeError):
        proof_plan(
            repo,
            head=head,
            expected_commitment_digest="0" * 64,
        )


def test_proof_plan_rejects_a_change_for_another_repository(tmp_path: Path) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    commitment = repo / "openspec" / "changes" / "proof-binding" / "commitment.toml"
    commitment.write_text(
        commitment.read_text(encoding="utf-8").replace(
            'subjects = ["repository:self"]',
            'subjects = ["repository:foreign"]',
        ),
        encoding="utf-8",
    )
    head = _commit(repo, "bind foreign repository")

    assert proof_plan(repo, head=head, change_id="proof-binding").gaps() == (
        "repository_subject_mismatch",
    )


def test_proof_plan_identity_is_stable_across_linked_worktrees(tmp_path: Path) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    linked = tmp_path / "repo-linked"
    subprocess.run(
        ["git", "worktree", "add", "--detach", linked.as_posix(), head],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )

    assert proof_plan(repo, head=head).digest() == proof_plan(linked, head=head).digest()


def test_gate_policy_uses_one_dependency_closure_for_nodes_and_digest(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _write_script_gate_policy(repo)
    first_head = _commit(repo, "first policy")

    policy = resolve_gate_policy(repo, tree_ref=first_head)
    nodes, gaps = policy.nodes, policy.gaps
    first_digest = policy.digest

    assert gaps == ()
    assert tuple(node.id for node in nodes) == ("check", "publish")

    registry = repo / "system" / "gates.toml"
    registry.write_text(
        registry.read_text(encoding="utf-8").replace(
            'command = ["tools/check.sh"]',
            'command = ["tools/check-v2.sh"]',
        ),
        encoding="utf-8",
    )
    (repo / "tools" / "check-v2.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    second_head = _commit(repo, "change dependency command")

    assert resolve_gate_policy(repo, tree_ref=second_head).digest != first_digest


def test_committed_gate_policy_never_reads_missing_source_from_worktree(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _write_script_gate_policy(repo)
    _commit(repo, "policy with source")
    (repo / "tools" / "check.sh").unlink()
    head_without_source = _commit(repo, "remove source")
    (repo / "tools" / "check.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")

    gaps = resolve_gate_policy(repo, tree_ref=head_without_source).gaps

    assert gaps == ("gate_policy_source_missing:check:tools/check.sh",)


def test_gate_policy_digest_binds_profile_correctness_semantics(tmp_path: Path) -> None:
    repo, first_head = _adopted_repo(tmp_path / "repo")
    first = resolve_gate_policy(repo, tree_ref=first_head).digest
    profile = repo / ".ethos" / "profile.toml"

    profile.write_text(
        profile.read_text(encoding="utf-8").replace(
            'dimensions = ["test", "coverage"]',
            'dimensions = ["test", "coverage", "property"]',
        ),
        encoding="utf-8",
    )
    dimensions_head = _commit(repo, "change dimensions")
    dimensions = resolve_gate_policy(repo, tree_ref=dimensions_head).digest

    profile.write_text(
        profile.read_text(encoding="utf-8").replace(
            'static-analysis = "sample-static"',
            'static-analysis = "sample-tests"',
        ),
        encoding="utf-8",
    )
    invalid_head = _commit(repo, "reuse one gate for two axes")

    assert first != dimensions
    with pytest.raises(ValueError, match="repository_profile_invalid"):
        resolve_gate_policy(repo, tree_ref=invalid_head)


def test_gate_command_normalization_preserves_explicit_python_version() -> None:
    assert canonical_gate_command(("/one/bin/python3.14", "-m", "tool")) == (
        "python",
        "-m",
        "tool",
    )
    assert canonical_gate_command(("/two/bin/python3.13", "-m", "tool")) == (
        "python",
        "-m",
        "tool",
    )
    assert canonical_gate_command(("python3.12", "-m", "tool")) != canonical_gate_command(
        ("python3.13", "-m", "tool")
    )


def test_proof_plan_identity_changes_with_commitment_head_or_policy(tmp_path: Path) -> None:
    repo, first_head = _adopted_repo(tmp_path / "repo")
    first = proof_plan(repo, head=first_head)

    commitment = repo / "openspec" / "changes" / "proof-binding" / "commitment.toml"
    commitment.write_text(
        commitment.read_text(encoding="utf-8").replace(
            "Bind proof to the governed change.",
            "Bind the revised proof to the governed change.",
        ),
        encoding="utf-8",
    )
    commitment_head = _commit(repo, "revise commitment")
    commitment_changed = proof_plan(repo, head=commitment_head)

    gates = repo / "system" / "gates.toml"
    gates.parent.mkdir()
    gates.write_text("[proof_sets]\ndefault = []\nfull = []\n", encoding="utf-8")
    policy_head = _commit(repo, "revise policy")
    policy_changed = proof_plan(repo, head=policy_head)

    assert len({first.digest(), commitment_changed.digest(), policy_changed.digest()}) == 3


def test_proof_plan_requires_a_change_selector_when_multiple_active_commitments_exist(
    tmp_path: Path,
) -> None:
    repo, _head = _adopted_repo(tmp_path / "repo")
    second = repo / "openspec" / "changes" / "second"
    second.mkdir()
    (second / "commitment.toml").write_text(
        'schema_version = 1\nid = "change:second"\nintent = "Second change."\n'
        'subjects = ["repository:self"]\nscope = ["**"]\n',
        encoding="utf-8",
    )
    head = _commit(repo, "add second change")

    with pytest.raises(ValueError, match="commitment_ambiguous"):
        proof_plan(repo, head=head)

    selected = proof_plan(repo, head=head, change_id="proof-binding")

    assert selected.facts["values"]["change_id"] == "proof-binding"


def test_proof_plan_ignores_complete_commitment_at_committed_head(tmp_path: Path) -> None:
    repo, _head = _adopted_repo(tmp_path / "repo")
    active_tasks = repo / "openspec" / "changes" / "proof-binding" / "tasks.md"
    active_tasks.write_text("- [ ] Prove\n", encoding="utf-8")
    complete = repo / "openspec" / "changes" / "complete"
    complete.mkdir()
    (complete / "commitment.toml").write_text(
        'schema_version = 1\nid = "change:complete"\nintent = "Complete."\n'
        'subjects = ["repository:self"]\nscope = ["**"]\n',
        encoding="utf-8",
    )
    (complete / "tasks.md").write_text("- [x] Done\n", encoding="utf-8")
    head = _commit(repo, "add complete historical change")

    assert proof_plan(repo, head=head).facts["values"]["change_id"] == "proof-binding"
    with pytest.raises(ValueError, match="commitment_complete:complete"):
        proof_plan(repo, head=head, change_id="complete")


def test_proof_plan_uses_repository_commitment_when_no_active_commitment_exists(
    tmp_path: Path,
) -> None:
    repo, _head = _adopted_repo(tmp_path / "repo")
    tasks = repo / "openspec" / "changes" / "proof-binding" / "tasks.md"
    tasks.write_text("- [x] Complete\n", encoding="utf-8")
    head = _commit(repo, "complete the only change")

    plan = proof_plan(repo, head=head)

    assert plan.commitment_digest == load_repository_commitment(repo, tree_ref=head).digest()
    assert plan.facts["values"]["change_id"] == ""


def test_proof_attestation_is_content_addressed_and_exactly_bound(tmp_path: Path) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    plan = proof_plan(repo, head=head)
    attestation = _proof_attestation(repo, head)

    path = persist_proof_attestation(repo, attestation)

    assert path == attestation_store_dir(repo) / f"{attestation.id}.json"
    assert path.read_text(encoding="utf-8") == attestation.canonical_json()
    assert attestation.predicate == "proof:execution"
    assert attestation.subject == f"git:commit:{head}"
    assert attestation.verdict == "pass"
    assert attestation.commitment_digest == plan.commitment_digest
    assert attestation.facts_digest == plan.facts_digest
    assert attestation.plan_digest == plan.digest()
    assert attestation.policy_digest == plan.policy_digest
    assert attestation.effect_digest
    assert attestation.evidence_refs == (f"sha256:{attestation.effect_digest}",)
    assert attestation.valid_from == attestation.issued_at
    assert attestation.statement["scope"] == ("repository",)
    assert attestation.statement["plane"] == "local"
    assert attestation.statement["context"] == {"boundary": "repository"}
    assert proof_attestation(repo, head) == attestation
    assert proof_gaps(repo, head) == []


def test_legacy_head_keyed_proof_file_is_immediately_inert(tmp_path: Path) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    legacy = repo / ".ethos" / "state" / "proof" / f"{head}.json"
    legacy.parent.mkdir(parents=True)
    legacy.write_text(
        json.dumps({"schema_version": 4, "head": head, "state": "proven"}),
        encoding="utf-8",
    )

    assert proof_attestation(repo, head) is None
    assert proof_gaps(repo, head) == ["proof_not_proven"]


def test_proof_attestation_artifact_tamper_fails_closed(tmp_path: Path) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    attestation = _proof_attestation(repo, head)
    persist_proof_attestation(repo, attestation)
    artifact = attestation.statement["artifact"]
    assert isinstance(artifact, Mapping)
    artifact_path = attestation_store_dir(repo) / str(artifact["path"])
    artifact_path.write_text("tampered", encoding="utf-8")

    assert proof_attestation(repo, head) is None
    assert proof_gaps(repo, head) == ["proof_attestation_artifact_digest_mismatch"]


def test_proof_attestation_binding_mismatch_fails_closed_even_with_valid_peer(
    tmp_path: Path,
) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    valid = _proof_attestation(repo, head)
    persist_proof_attestation(repo, valid)
    forged = Attestation.issue(
        {
            "predicate": "proof:execution",
            "verifier": valid.verifier,
            "subject": valid.subject,
            "issued_at": datetime(2026, 7, 26, 0, 0, 1, tzinfo=UTC),
            "verdict": "pass",
            "statement": valid.statement,
            "evidence_refs": valid.evidence_refs,
            "commitment_digest": valid.commitment_digest,
            "facts_digest": valid.facts_digest,
            "plan_digest": "0" * 64,
            "policy_digest": valid.policy_digest,
            "effect_digest": valid.effect_digest,
        }
    )
    store = attestation_store_dir(repo)
    (store / f"{forged.id}.json").write_text(forged.canonical_json(), encoding="utf-8")

    assert proof_attestation(repo, head) is None
    assert proof_gaps(repo, head) == ["proof_attestation_binding_mismatch:plan_digest"]


def test_proof_attestation_persistence_replays_identity_and_rejects_collision(
    tmp_path: Path,
) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    attestation = _proof_attestation(repo, head)
    path = persist_proof_attestation(repo, attestation)

    assert persist_proof_attestation(repo, attestation) == path
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="attestation_identity_collision"):
        persist_proof_attestation(repo, attestation)


def test_proof_admission_uses_self_contained_closure_not_historical_commitment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    attestation = _proof_attestation(repo, head)
    persist_proof_attestation(repo, attestation)

    def historical_read_forbidden(*_args: object, **_kwargs: object) -> object:
        message = "historical_commitment_read"
        raise AssertionError(message)

    monkeypatch.setattr(proof_module, "load_profile_commitment", historical_read_forbidden)
    monkeypatch.setattr(proof_module, "load_repository_commitment", historical_read_forbidden)

    assert proof_attestation(repo, head) == attestation
    assert proof_gaps(repo, head) == []


def test_proof_authority_conflict_blocks_instead_of_selecting_latest(tmp_path: Path) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    first = _proof_attestation(repo, head)
    persist_proof_attestation(repo, first)
    conflicting = Attestation.issue(
        {
            "predicate": first.predicate,
            "verifier": "agent:test:case:conflict",
            "subject": first.subject,
            "issued_at": first.issued_at,
            "valid_from": first.valid_from,
            "verdict": first.verdict,
            "statement": first.statement | {"objective": "conflicting proof meaning"},
            "evidence_refs": first.evidence_refs,
            "commitment_digest": first.commitment_digest,
            "facts_digest": first.facts_digest,
            "plan_digest": first.plan_digest,
            "policy_digest": first.policy_digest,
            "effect_digest": first.effect_digest,
        }
    )
    persist_proof_attestation(repo, conflicting)

    assert proof_attestation(repo, head) is None
    assert proof_gaps(repo, head) == ["contradiction"]


def test_proof_authority_selects_the_latest_equivalent_attestation(tmp_path: Path) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    first = _proof_attestation(repo, head)
    persist_proof_attestation(repo, first)
    later = next(
        candidate
        for seconds in range(1, 100)
        if (
            candidate := Attestation.issue(
                first.model_dump(exclude={"id", "schema_version", "statement_digest"})
                | {"issued_at": first.issued_at + timedelta(seconds=seconds)}
            )
        ).id
        > first.id
    )
    persist_proof_attestation(repo, later)

    assert proof_attestation(repo, head) == later
