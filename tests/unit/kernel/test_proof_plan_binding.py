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
from ethos.adapters.mutation.proof_artifacts import artifact_checks
from ethos.adapters.mutation.proof_artifacts import write_proof_artifact
from ethos.adapters.openspec.profile import load_profile_commitment
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.gate_policy import resolve_gate_policy
from ethos.contracts.plan import PlanInputs
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import compile_plan
from ethos.contracts.plan import proof_effect_projection
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import Commitment
from ethos.contracts.semantic import Facts
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.value import mutable_json
from ethos.repository.adoption.planner import adoption_plan
from ethos.repository.policy.gates import canonical_gate_command
from ethos.repository.policy.gates import gate_execution_identity
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import start_adopted_work_lane

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


def _write_script_gate_policy(root: Path, *, full: bool = False) -> None:
    profile = root / ".ethos/profile.toml"
    profile.parent.mkdir(parents=True, exist_ok=True)
    profile.write_text(
        'profile_id = "policy-test"\n\n[proof]\ngate_registry = "system/gates.toml"\n',
        encoding="utf-8",
    )
    registry = root / "system/gates.toml"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(
        'schema_version = 1\nid = "policy-test"\n\n'
        f"[proof_sets]\ndefault = [{'"check"' if full else '"publish"'}]\n"
        f"full = [{'"check", "publish"'}]\n\n"
        '[[gates]]\nid = "publish"\nregistries = ["runtime"]\nkind = "release"\n'
        'command = ["publish"]\ndepends_on = ["check"]\n\n'
        '[[gates]]\nid = "check"\nregistries = ["runtime"]\nkind = "test"\n'
        'command = ["tools/check.sh"]\ndimensions = ["behavior"]\n'
        'evidence_class = "proof"\ntrust_bearing = true\n',
        encoding="utf-8",
    )
    script = root / "tools/check.sh"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")


def _adopted_repo(path: Path) -> tuple[Path, str]:
    repo = init_git_repo(path)
    adoption_plan(repo, apply=True)
    profile = repo / ".ethos/profile.toml"
    profile.write_text(
        profile.read_text(encoding="utf-8")
        + """
+[proof]
+code_correctness_gates = ["sample-tests", "sample-static"]
+[proof.code_correctness_map]
+behavior = "sample-tests"
+static-analysis = "sample-static"
+[[proof.gates]]
+id = "sample-tests"
+kind = "test"
+command = ["sample", "test"]
+dimensions = ["test", "coverage"]
+execution_mode = "subprocess"
+evidence_class = "proof"
+trust_bearing = true
+tool_adapter = "repository-native"
+[[proof.gates]]
+id = "sample-static"
+kind = "typing"
+command = ["sample", "typecheck"]
+dimensions = ["static-analysis"]
+execution_mode = "subprocess"
+evidence_class = "contract"
+trust_bearing = true
+tool_adapter = "repository-native"
+""".replace("+", ""),
        encoding="utf-8",
    )
    (repo / ".ethos/commitment.toml").write_text(
        'schema_version = 1\nid = "repository:repo"\nintent = "Govern this adopted repository."\n'
        'subjects = ["repository:repo"]\nscope = ["**"]\n'
        'permissions = ["repository.read", "git.ref.compare-and-swap"]\n',
        encoding="utf-8",
    )
    carrier = repo / "openspec/changes/proof-binding"
    carrier.mkdir(parents=True)
    (carrier / "commitment.toml").write_text(
        'schema_version = 1\nid = "change:proof-binding"\n'
        'intent = "Bind proof to the governed change."\nsubjects = ["repository:self"]\n'
        'scope = ["**"]\npermissions = ["repository.read"]\n',
        encoding="utf-8",
    )
    return repo, _commit(repo, "adopt and bind proof")


def _proof_checks(root: Path, head: str, *, full: bool = False) -> tuple[dict[str, object], ...]:
    policy = resolve_gate_policy(root, tree_ref=head, full=full)
    return tuple(
        {
            "action_id": gate.id,
            "command": list(gate_execution_identity(gate)),
            "exit_code": 0,
            "stdout": f"{gate.id} passed",
            "stderr": "",
            "verdict": "pass",
            "evidence_class": gate.evidence_class,
            "trust_bearing": gate.trust_bearing,
            "diagnostics": [],
        }
        for gate in policy.gates
    )


def _issue(
    root: Path,
    head: str,
    *,
    plan: TransitionPlan | None = None,
    checks: tuple[dict[str, object], ...] | None = None,
    issuer: str = "agent:test:case:proof",
    issued_at: datetime | None = datetime(2026, 7, 26, tzinfo=UTC),
    boundary: str = "repository",
) -> Attestation:
    return issue_proof_attestation(
        root,
        {
            "plan": plan or proof_plan(root, head=head),
            "checks": checks or _proof_checks(root, head),
            "verdict": "pass",
            "issuer": issuer,
            **({"issued_at": issued_at} if issued_at else {}),
            "scope": "repository",
            "boundary": boundary,
        },
    )


def _reissue(record: Attestation, **updates: object) -> Attestation:
    payload = record.model_dump(mode="python", exclude={"id", "schema_version", "statement_digest"})
    return Attestation.issue(payload | updates)


def _store(root: Path, record: Attestation) -> None:
    store = attestation_store_dir(root)
    store.mkdir(parents=True, exist_ok=True)
    (store / f"{record.id}.json").write_text(record.canonical_json(), encoding="utf-8")


def _assert_proof(
    root: Path, head: str, *, selected: Attestation | None = None, gap: str | None = None
) -> None:
    assert proof_attestation(root, head) == selected
    assert proof_gaps(root, head) == ([] if gap is None else [gap])


def _forged_proof(
    valid: Attestation,
    plan: TransitionPlan,
    *,
    statement: Mapping[str, object] | None = None,
    evidence_refs: tuple[str, ...] | None = None,
) -> Attestation:
    payload = valid.model_dump(
        mode="python", exclude={"id", "schema_version", "statement_digest"}
    ) | {
        "commitment_digest": plan.inputs.commitment,
        "facts_digest": plan.inputs.facts,
        "plan_digest": plan.digest,
        "policy_digest": plan.inputs.policy,
        "effect_digest": plan.inputs.effect,
        "statement": valid.statement | {"plan": plan.model_dump(mode="json"), **(statement or {})},
    }
    if evidence_refs is not None:
        payload["evidence_refs"] = evidence_refs
    return Attestation.issue(payload)


def _compile_variant(
    plan: TransitionPlan,
    *,
    policy: dict[str, object] | None = None,
    facts: Facts | None = None,
    nodes=None,
    effect: dict[str, object] | None = None,
) -> TransitionPlan:
    policy = policy or dict(plan.policy)
    facts = facts or Facts.model_validate(plan.facts | {"observed_at": datetime.now(UTC)})
    nodes = plan.nodes if nodes is None else nodes
    effect = effect or proof_effect_projection(
        commitment=plan.inputs.commitment,
        facts=facts.digest(),
        policy=canonical_json_digest(policy),
        nodes=nodes,
    )
    return TransitionPlan.compile(
        inputs=PlanInputs(
            commitment=plan.inputs.commitment,
            facts=facts.digest(),
            prior_attestations=plan.inputs.prior_attestations,
            policy=canonical_json_digest(policy),
            effect=canonical_json_digest(effect),
        ),
        closure={
            "commitment": plan.commitment,
            "prior_attestations": plan.prior_attestations,
            "policy": policy,
            "effect": effect,
        },
        permissions=plan.permissions,
        facts=facts.model_dump(mode="json", exclude={"observed_at"}),
        nodes=nodes,
        verdict=plan.verdict,
        required_gaps=plan.required_gaps,
    )


def test_work_lane_proof_plan_uses_the_current_active_commitment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    holder = "agent:test:case:current-commitment"
    root = start_adopted_work_lane(tmp_path, holder_ref=holder).worktree
    branch = git(root, "branch", "--show-current")
    lease = proof_module.leases_by_branch(root)[branch]
    carrier = root / str(lease["base_commitment_path"])
    carrier.write_text(
        carrier.read_text() + 'acceptance = ["current working-tree intent is planned"]\n'
    )
    monkeypatch.setenv("ETHOS_ACTOR", holder)
    plan = proof_plan(root, head=git(root, "rev-parse", "HEAD"))
    assert plan.inputs.commitment == load_profile_commitment(root).digest()
    assert plan.inputs.commitment != lease["base_commitment_digest"]
    assert plan.commitment["acceptance"] == ("current working-tree intent is planned",)


def test_proof_plan_binds_identity_and_rejects_escape_hatches(tmp_path: Path) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    plan = proof_plan(repo, head=head)
    assert plan.inputs.model_dump(mode="json") == plan.model_dump(mode="json")["inputs"]
    assert plan.facts["values"]["change_id"] == "proof-binding"
    assert plan.permissions == ("repository.read",)
    with pytest.raises(TypeError):
        proof_plan(repo, head=head, expected_commitment_digest="0" * 64)
    carrier = repo / "openspec/changes/proof-binding/commitment.toml"
    carrier.write_text(carrier.read_text().replace("repository:self", "repository:foreign"))
    foreign_head = _commit(repo, "bind foreign repository")
    assert proof_plan(repo, head=foreign_head, change_id="proof-binding").required_gaps == (
        "repository_subject_mismatch",
    )


def test_proof_plan_identity_is_stable_across_worktrees_and_changes_with_inputs(
    tmp_path: Path,
) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    linked = tmp_path / "linked"
    subprocess.run(["git", "worktree", "add", "--detach", str(linked), head], cwd=repo, check=True)
    first = proof_plan(repo, head=head)
    assert first.digest == proof_plan(linked, head=head).digest
    carrier = repo / "openspec/changes/proof-binding/commitment.toml"
    carrier.write_text(carrier.read_text().replace("Bind proof", "Bind revised proof"))
    commitment_changed = proof_plan(repo, head=_commit(repo, "commitment"))
    (repo / "system/gates.toml").parent.mkdir(exist_ok=True)
    (repo / "system/gates.toml").write_text("[proof_sets]\ndefault=[]\nfull=[]\n")
    policy_changed = proof_plan(repo, head=_commit(repo, "policy"))
    assert len({first.digest, commitment_changed.digest, policy_changed.digest}) == 3


def test_gate_policy_closure_sources_runtime_and_semantics(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _write_script_gate_policy(repo)
    first_head = _commit(repo, "policy")
    first = resolve_gate_policy(repo, tree_ref=first_head)
    assert (tuple(node.id for node in first.nodes), first.gaps) == (("check", "publish"), ())
    registry = repo / "system/gates.toml"
    registry.write_text(registry.read_text().replace("tools/check.sh", "tools/check-v2.sh"))
    (repo / "tools/check-v2.sh").write_text("#!/bin/sh\nexit 0\n")
    assert resolve_gate_policy(repo, tree_ref=_commit(repo, "command")).digest != first.digest
    (repo / "tools/check-v2.sh").unlink()
    missing_head = _commit(repo, "missing")
    (repo / "tools/check-v2.sh").write_text("#!/bin/sh\nexit 0\n")
    assert resolve_gate_policy(repo, tree_ref=missing_head).gaps == (
        "gate_policy_source_missing:check:tools/check-v2.sh",
    )


def test_nox_policy_binds_repository_sources_and_fails_without_runtime(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _write_script_gate_policy(repo)
    registry = repo / "system/gates.toml"
    registry.write_text(
        registry.read_text().replace(
            '["tools/check.sh"]', '["{python}", "-m", "nox", "-s", "check"]'
        )
    )
    for path, text in (
        ("noxfile.py", "def check(): pass\n"),
        ("pyproject.toml", "[project]\nname='x'\nversion='0'\n"),
        ("uv.lock", "version=1\n"),
    ):
        (repo / path).write_text(text)
    missing = _commit(repo, "nox no runtime")
    assert resolve_gate_policy(repo, tree_ref=missing).gaps == (
        "gate_runtime_missing:repository-python",
    )
    runtime = repo / ".venv/bin/python"
    runtime.parent.mkdir(parents=True)
    runtime.write_text("")
    bound = resolve_gate_policy(repo, tree_ref=_commit(repo, "nox runtime"))
    assert bound.gaps == ()
    assert {path for path, _ in bound.sources[0][1]} == {"noxfile.py", "pyproject.toml", "uv.lock"}


def test_gate_policy_order_profile_semantics_and_python_command_normalization(
    tmp_path: Path,
) -> None:
    repo, _ = _adopted_repo(tmp_path / "repo")
    profile = repo / ".ethos/profile.toml"
    first = resolve_gate_policy(repo, tree_ref=git(repo, "rev-parse", "HEAD")).digest
    profile.write_text(
        profile.read_text().replace(
            'dimensions = ["test", "coverage"]', 'dimensions = ["test", "coverage", "property"]'
        )
    )
    assert resolve_gate_policy(repo, tree_ref=_commit(repo, "dimensions")).digest != first
    profile.write_text(
        profile.read_text().replace(
            'static-analysis = "sample-static"', 'static-analysis = "sample-tests"'
        )
    )
    with pytest.raises(ValueError, match="repository_profile_invalid"):
        resolve_gate_policy(repo, tree_ref=_commit(repo, "invalid map"))
    assert canonical_gate_command(("/one/bin/python3.14", "-m", "tool")) == ("python", "-m", "tool")
    assert canonical_gate_command(("python3.12", "-m", "tool")) != canonical_gate_command(
        ("python3.13", "-m", "tool")
    )


def test_change_selection_preserves_unarchived_authority(tmp_path: Path) -> None:
    repo, _ = _adopted_repo(tmp_path / "repo")
    second = repo / "openspec/changes/second"
    second.mkdir()
    (second / "commitment.toml").write_text(
        'schema_version=1\nid="change:second"\nintent="Second"\nsubjects=["repository:self"]\nscope=["**"]\n'
    )
    head = _commit(repo, "second")
    with pytest.raises(ValueError, match="commitment_ambiguous"):
        proof_plan(repo, head=head)
    assert (
        proof_plan(repo, head=head, change_id="proof-binding").facts["values"]["change_id"]
        == "proof-binding"
    )
    (second / "tasks.md").write_text("- [x] Done\n")
    (repo / "openspec/changes/proof-binding/tasks.md").write_text("- [x] Complete\n")
    head = _commit(repo, "complete")
    with pytest.raises(ValueError, match="commitment_ambiguous"):
        proof_plan(repo, head=head)
    plan = proof_plan(repo, head=head, change_id="proof-binding")
    assert plan.inputs.commitment != load_repository_commitment(repo, tree_ref=head).digest()


def test_proof_attestation_is_content_addressed_and_exactly_bound(tmp_path: Path) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    plan, record = proof_plan(repo, head=head), _issue(repo, head)
    path = persist_proof_attestation(repo, record)
    assert path == attestation_store_dir(repo) / f"{record.id}.json"
    assert path.read_text() == record.canonical_json()
    assert (record.predicate, record.subject, record.verdict) == (
        "proof:execution",
        f"git:commit:{head}",
        "pass",
    )
    assert (
        record.commitment_digest,
        record.facts_digest,
        record.plan_digest,
        record.policy_digest,
    ) == (plan.inputs.commitment, plan.inputs.facts, plan.digest, plan.inputs.policy)
    artifact = record.statement["artifact"]
    assert isinstance(artifact, Mapping)
    digest = str(artifact["sha256"]).removeprefix("sha256:")
    assert record.effect_digest == plan.inputs.effect != digest
    assert record.evidence_refs == (f"sha256:{digest}",)
    assert record.valid_from == record.issued_at
    assert mutable_json(record.statement["plan"]) == plan.model_dump(mode="json")
    assert set(record.statement) == {
        "artifact",
        "boundary",
        "claim",
        "context",
        "plan",
        "plane",
        "required_gaps",
        "scope",
    }
    _assert_proof(repo, head, selected=record)


@pytest.mark.parametrize("drift", ["nodes", "gaps"])
def test_transition_plan_rejects_policy_projection_divergence(tmp_path: Path, drift: str) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    plan = proof_plan(repo, head=head)
    policy = dict(plan.policy)
    policy["gates" if drift == "nodes" else "gaps"] = (
        list(policy["gates"][:-1])
        if drift == "nodes"
        else ["gate_policy_source_missing:sample-tests"]
    )
    with pytest.raises(ValueError, match="transition_plan_policy_node_mismatch"):
        _compile_variant(plan, policy=policy)


@pytest.mark.parametrize(
    ("field", "value", "gap"),
    [
        ("claim", {"objective": "other", "verdict": "block"}, "proof_attestation_claim_mismatch"),
        ("scope", [], "proof_attestation_scope_mismatch"),
        ("plane", "hosted", "proof_attestation_plane_mismatch"),
        ("context", {}, "proof_attestation_context_mismatch"),
        ("boundary", "other", "proof_attestation_boundary_mismatch"),
    ],
)
def test_proof_predicate_evidence_drift_fails_closed(
    tmp_path: Path, field: str, value: object, gap: str
) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    valid = _issue(repo, head)
    _store(repo, _reissue(valid, statement=valid.statement | {field: value}))
    _assert_proof(repo, head, gap=gap)


def test_unmappable_facts_and_live_policy_drift_fail_closed(tmp_path: Path) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    valid = _issue(repo, head)
    persist_proof_attestation(repo, valid)
    _store(repo, _reissue(valid, statement=valid.statement | {"novel_semantics": True}))
    _assert_proof(repo, head, gap="model_gap")
    fresh, fresh_head = _adopted_repo(tmp_path / "fresh")
    persist_proof_attestation(fresh, _issue(fresh, fresh_head))
    profile = fresh / ".ethos/profile.toml"
    profile.write_text(
        profile.read_text().replace(
            '["sample", "typecheck"]', '["sample", "typecheck", "--strict"]'
        )
    )
    _assert_proof(fresh, _commit(fresh, "policy drift"), gap="proof_not_proven")


def test_plan_model_gap_and_live_facts_drift_block_issuance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    plan = proof_plan(repo, head=head)
    fact = Facts.model_validate(
        plan.facts
        | {"observed_at": datetime.now(UTC), "values": plan.facts["values"] | {"novel": True}}
    )
    with pytest.raises(ValueError, match="transition_plan_model_gap"):
        _compile_variant(plan, facts=fact)
    monkeypatch.setattr(proof_module, "current_tree", lambda *_args, **_kwargs: "0" * 40)
    with pytest.raises(ValueError, match="proof_attestation_live_facts_stale"):
        _issue(repo, head, plan=plan, issued_at=None)


def test_head_and_subject_relabel_drift_fail_closed(tmp_path: Path) -> None:
    repo, first = _adopted_repo(tmp_path / "repo")
    plan = proof_plan(repo, head=first)
    (repo / "DRIFT.md").write_text("drift\n")
    _commit(repo, "move head")
    with pytest.raises(ValueError, match="proof_attestation_live_facts_stale"):
        _issue(repo, first, plan=plan, issued_at=None)
    second = git(
        repo, "commit-tree", "HEAD^{tree}", "-p", git(repo, "rev-parse", "HEAD"), "-m", "empty"
    )
    git(repo, "update-ref", "refs/heads/dev", second)
    record = _issue(repo, second)
    artifact = write_proof_artifact(attestation_store_dir(repo), first, _proof_checks(repo, second))
    digest = str(artifact["sha256"]).removeprefix("sha256:")
    forged = _reissue(
        record,
        subject=f"git:commit:{first}",
        statement=record.statement | {"head": first, "artifact": artifact},
        effect_digest=digest,
        evidence_refs=(f"sha256:{digest}",),
    )
    _store(repo, forged)
    assert proof_gaps(repo, first) == ["proof_attestation_plan_head_mismatch"]


def test_query_predicate_legacy_artifact_and_binding_fail_closed(tmp_path: Path) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    focused = _issue(repo, head, boundary="focused")
    persist_proof_attestation(repo, focused)
    _assert_proof(repo, head, gap="proof_attestation_context_mismatch")
    store = attestation_store_dir(repo)
    for record, gap in (
        (_reissue(_issue(repo, head), predicate="experiment:novel"), "proof_not_proven"),
        (
            _reissue(_issue(repo, head), plan_digest="0" * 64),
            "proof_attestation_binding_mismatch:plan_digest",
        ),
    ):
        for path in store.glob("*.json"):
            path.unlink()
        _store(repo, record)
        _assert_proof(repo, head, gap=gap)
    legacy = repo / ".ethos/state/proof" / f"{head}.json"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text(json.dumps({"schema_version": 4, "head": head, "state": "proven"}))
    for path in store.glob("*.json"):
        path.unlink()
    _assert_proof(repo, head, gap="proof_not_proven")
    valid = _issue(repo, head)
    persist_proof_attestation(repo, valid)
    artifact = valid.statement["artifact"]
    assert isinstance(artifact, Mapping)
    (store / str(artifact["path"])).write_text("tampered")
    _assert_proof(repo, head, gap="proof_attestation_artifact_digest_mismatch")


def test_persistence_identity_and_self_contained_closure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    record = _issue(repo, head)
    path = persist_proof_attestation(repo, record)
    assert persist_proof_attestation(repo, record) == path
    monkeypatch.setattr(
        proof_module,
        "load_profile_commitment",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError()),
    )
    monkeypatch.setattr(
        proof_module,
        "load_repository_commitment",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError()),
    )
    _assert_proof(repo, head, selected=record)
    path.write_text("{}")
    with pytest.raises(ValueError, match="attestation_identity_collision"):
        persist_proof_attestation(repo, record)


def test_self_consistent_scope_effect_and_policy_bypasses_fail_closed(tmp_path: Path) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    plan = proof_plan(repo, head=head, changed_paths=("src/feature.py",))
    arbitrary = {"operation": "arbitrary"}
    with pytest.raises(ValueError, match="transition_plan_effect_mismatch"):
        TransitionPlan.compile(
            inputs=plan.inputs.model_copy(update={"effect": canonical_json_digest(arbitrary)}),
            closure={
                "commitment": plan.commitment,
                "prior_attestations": plan.prior_attestations,
                "policy": plan.policy,
                "effect": arbitrary,
            },
            permissions=plan.permissions,
            facts=plan.facts,
            nodes=plan.nodes,
        )
    commitment = dict(plan.commitment) | {"scope": ["docs/**"]}
    digest = canonical_json_digest(commitment)
    effect = proof_effect_projection(
        commitment=digest, facts=plan.inputs.facts, policy=plan.inputs.policy, nodes=plan.nodes
    )
    with pytest.raises(ValueError, match="transition_plan_semantics_mismatch"):
        TransitionPlan.compile(
            inputs=PlanInputs(
                commitment=digest,
                facts=plan.inputs.facts,
                policy=plan.inputs.policy,
                effect=canonical_json_digest(effect),
            ),
            closure={
                "commitment": commitment,
                "prior_attestations": plan.prior_attestations,
                "policy": plan.policy,
                "effect": effect,
            },
            permissions=tuple(commitment["permissions"]),
            facts=plan.facts,
            nodes=plan.nodes,
        )
    policy = dict(plan.policy) | {"noncanonical": True}
    forged = _forged_proof(_issue(repo, head), _compile_variant(plan, policy=policy))
    _store(repo, forged)
    _assert_proof(repo, head, gap="proof_attestation_repository_policy_mismatch")


def test_gate_omission_and_nonexistent_tree_fail_closed(tmp_path: Path) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    valid, plan = _issue(repo, head), proof_plan(repo, head=head)
    nodes = plan.nodes[:-1]
    policy = dict(plan.policy)
    policy["gates"] = list(policy["gates"][:-1])
    values = dict(plan.facts["values"]) | {"gate_ids": [node.id for node in nodes]}
    facts = Facts(
        repository=str(plan.facts["repository"]),
        head=head,
        tree=str(plan.facts["tree"]),
        observed_at=datetime.now(UTC),
        values=values,
        source_refs=tuple(plan.facts["source_refs"]),
    )
    forged_plan = _compile_variant(plan, policy=policy, facts=facts, nodes=nodes)
    checks = _proof_checks(repo, head)[:-1]
    artifact = write_proof_artifact(attestation_store_dir(repo), head, checks)
    digest = str(artifact["sha256"]).removeprefix("sha256:")
    _store(
        repo,
        _forged_proof(
            valid,
            forged_plan,
            statement={"artifact": artifact},
            evidence_refs=(f"sha256:{digest}",),
        ),
    )
    _assert_proof(repo, head, gap="proof_attestation_repository_policy_mismatch")
    for path in attestation_store_dir(repo).glob("*.json"):
        path.unlink()
    nonexistent = Facts.model_validate(
        plan.facts | {"observed_at": datetime.now(UTC), "tree": "0" * 40}
    )
    _store(repo, _forged_proof(valid, _compile_variant(plan, facts=nonexistent)))
    _assert_proof(repo, head, gap="proof_attestation_live_tree_mismatch")


def test_repository_admission_prefers_full_proof(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _write_script_gate_policy(repo, full=True)
    (repo / ".ethos/commitment.toml").write_text(
        'schema_version=1\nid="repository:repo"\nintent="govern"\n'
        'subjects=["repository:repo"]\nscope=["**"]\n'
    )
    commitment = repo / "openspec/changes/proof-binding"
    commitment.mkdir(parents=True)
    (commitment / "commitment.toml").write_text(
        'schema_version=1\nid="change:proof-binding"\nintent="proof"\nsubjects=["repository:self"]\nscope=["**"]\n'
    )
    head = _commit(repo, "full floor")
    default = _issue(repo, head)
    persist_proof_attestation(repo, default)
    _assert_proof(repo, head, gap="full_proof_required")
    full_plan = proof_plan(repo, head=head, full=True)
    full = _issue(repo, head, plan=full_plan, checks=_proof_checks(repo, head, full=True))
    persist_proof_attestation(repo, full)
    assert default.plan_digest != full.plan_digest
    _assert_proof(repo, head, selected=full)


def test_equivalent_proofs_supersede_deterministically_but_conflicts_block(tmp_path: Path) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    first = _issue(repo, head)
    persist_proof_attestation(repo, first)
    later = _reissue(first, issued_at=first.issued_at + timedelta(seconds=1))
    persist_proof_attestation(repo, later)
    assert proof_attestation(repo, head).id == min(first.id, later.id)  # type: ignore[union-attr]
    conflict = _reissue(
        first,
        verifier="agent:test:case:conflict",
        statement=first.statement | {"claim": {"objective": "conflict", "verdict": "pass"}},
    )
    persist_proof_attestation(repo, conflict)
    _assert_proof(repo, head, gap="contradiction")


def test_equivalent_proofs_with_different_artifacts_share_closure(tmp_path: Path) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    first = _issue(repo, head)
    persist_proof_attestation(repo, first)
    checks = tuple(
        check | {"stdout": f"{check['stdout']} again"} for check in _proof_checks(repo, head)
    )
    second = _issue(repo, head, checks=checks, issued_at=first.issued_at + timedelta(seconds=1))
    persist_proof_attestation(repo, second)
    assert first.effect_digest == second.effect_digest
    assert first.evidence_refs != second.evidence_refs
    assert proof_attestation(repo, head) is not None
    assert proof_gaps(repo, head) == []


def _archive_plan(
    repo: Path, head: str, changed: tuple[str, ...], authorized: tuple[str, ...]
) -> TransitionPlan:
    base = proof_plan(repo, head=head, changed_paths=changed)
    facts = Facts.model_validate(
        base.facts
        | {
            "observed_at": datetime.now(UTC),
            "values": base.facts["values"] | {"changed_paths": changed},
        }
    )
    return compile_plan(
        Commitment.model_validate(dict(base.commitment)),
        facts,
        base.nodes,
        policy=dict(base.policy),
        prior_attestations={"openspec_archive": {"authorized_paths": list(authorized)}},
    )


def test_archive_authority_supersedes_historical_scope_and_requires_current_proof(
    tmp_path: Path,
) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    historical = _issue(
        repo, head, plan=_archive_plan(repo, head, ("historical.py", "current.py"), ("current.py",))
    )
    persist_proof_attestation(repo, historical)
    _assert_proof(repo, head, gap="proof_archive_scope_stale")
    current = _issue(repo, head, plan=_archive_plan(repo, head, ("current.py",), ("current.py",)))
    persist_proof_attestation(repo, current)
    _assert_proof(repo, head, selected=current)


@pytest.mark.parametrize("novel", [False, True])
def test_expired_or_other_query_proofs_do_not_pollute_current_authority(
    tmp_path: Path, *, novel: bool
) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    current = _issue(repo, head)
    persist_proof_attestation(repo, current)
    issued = datetime.now(UTC) - timedelta(minutes=2)
    _store(
        repo,
        _reissue(
            current,
            issued_at=issued,
            valid_from=issued,
            valid_until=issued + timedelta(minutes=1),
            **({"statement": current.statement | {"novel_semantics": True}} if novel else {}),
        ),
    )
    _assert_proof(repo, head, selected=current)
    _store(repo, _reissue(current, statement=current.statement | {"scope": ("workspace",)}))
    _assert_proof(repo, head, selected=current)


def test_policy_binding_and_artifact_descriptor_drift_fail_closed(tmp_path: Path) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    valid = _issue(repo, head)
    persist_proof_attestation(repo, valid)
    _store(repo, _reissue(valid, policy_digest="0" * 64))
    _assert_proof(repo, head, gap="proof_policy_digest_stale")
    descriptor = valid.statement["artifact"]
    assert isinstance(descriptor, Mapping)
    forged = _reissue(
        valid,
        statement=valid.statement
        | {"artifact": descriptor | {"media_type": "text/plain", "extra": "unbound"}},
    )
    assert artifact_checks(attestation_store_dir(repo), forged)[1] == [
        "proof_attestation_artifact_binding_mismatch"
    ]
