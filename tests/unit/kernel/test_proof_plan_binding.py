# ruff: noqa: E501
# fmt: off
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


def _eq(actual: object, expected: object) -> None:
    assert actual == expected


def _ne(actual: object, expected: object) -> None:
    assert actual != expected


def _true(value: object) -> None:
    assert value


def _raises(exception, match: str | None, call) -> None:
    with pytest.raises(exception, match=match):
        call()


def _commit(root: Path, message: str) -> str:
    (git(root, "add", "."), git(root, "-c", "user.name=Test User", "-c", "user.email=test@example.com", "commit", "-m", message))
    return git(root, "rev-parse", "HEAD")


def _repo(path: Path) -> tuple[Path, str]:
    repo = init_git_repo(path); adoption_plan(repo, apply=True); profile = repo / ".ethos/profile.toml"  # noqa: E702
    profile.write_text(profile.read_text() + '\n[proof]\ncode_correctness_gates=["sample-tests","sample-static"]\n[proof.code_correctness_map]\nbehavior="sample-tests"\nstatic-analysis="sample-static"\n[[proof.gates]]\nid="sample-tests"\nkind="test"\ncommand=["sample","test"]\ndimensions=["test","coverage"]\nexecution_mode="subprocess"\nevidence_class="proof"\ntrust_bearing=true\ntool_adapter="repository-native"\n[[proof.gates]]\nid="sample-static"\nkind="typing"\ncommand=["sample","typecheck"]\ndimensions=["static-analysis"]\nexecution_mode="subprocess"\nevidence_class="contract"\ntrust_bearing=true\ntool_adapter="repository-native"\n')
    (repo / ".ethos/commitment.toml").write_text('schema_version=1\nid="repository:repo"\nintent="Govern this adopted repository."\nsubjects=["repository:repo"]\nscope=["**"]\npermissions=["repository.read","git.ref.compare-and-swap"]\n')
    carrier = repo / "openspec/changes/proof-binding"; carrier.mkdir(parents=True)  # noqa: E702
    (carrier / "commitment.toml").write_text('schema_version=1\nid="change:proof-binding"\nintent="Bind proof to the governed change."\nsubjects=["repository:self"]\nscope=["**"]\npermissions=["repository.read"]\n')
    return repo, _commit(repo, "adopt and bind proof")


def _policy(root: Path, *, full: bool = False) -> None:
    tuple(path.mkdir(parents=True, exist_ok=True) for path in (root / ".ethos", root / "system", root / "tools"))
    (root / ".ethos/profile.toml").write_text('profile_id="policy-test"\n[proof]\ngate_registry="system/gates.toml"\n')
    (root / "system/gates.toml").write_text('schema_version=1\nid="policy-test"\n[proof_sets]\ndefault=[' + ('"check"' if full else '"publish"') + ']\nfull=["check","publish"]\n[[gates]]\nid="publish"\nregistries=["runtime"]\nkind="release"\ncommand=["publish"]\ndepends_on=["check"]\n[[gates]]\nid="check"\nregistries=["runtime"]\nkind="test"\ncommand=["tools/check.sh"]\ndimensions=["behavior"]\nevidence_class="proof"\ntrust_bearing=true\n')
    (root / "tools/check.sh").write_text("#!/bin/sh\nexit 0\n")


def _checks(root: Path, head: str, *, full: bool = False) -> tuple[dict[str, object], ...]:
    return tuple({"action_id": gate.id, "command": list(gate_execution_identity(gate)), "exit_code": 0, "stdout": f"{gate.id} passed", "stderr": "", "verdict": "pass", "evidence_class": gate.evidence_class, "trust_bearing": gate.trust_bearing, "diagnostics": []} for gate in resolve_gate_policy(root, tree_ref=head, full=full).gates)


def _issue(root: Path, head: str, *, plan: TransitionPlan | None = None, checks=None, issued_at: datetime | None = datetime(2026, 7, 26, tzinfo=UTC), boundary: str = "repository") -> Attestation:
    return issue_proof_attestation(root, {"plan": plan or proof_plan(root, head=head), "checks": checks or _checks(root, head), "verdict": "pass", "issuer": "agent:test:case:proof", **({"issued_at": issued_at} if issued_at else {}), "scope": "repository", "boundary": boundary})


def _reissue(record: Attestation, **updates: object) -> Attestation:
    return Attestation.issue(record.model_dump(mode="python", exclude={"id", "schema_version", "statement_digest"}) | updates)


def _store(root: Path, record: Attestation) -> None:
    store = attestation_store_dir(root); store.mkdir(parents=True, exist_ok=True); (store / f"{record.id}.json").write_text(record.canonical_json())  # noqa: E702


def _clear(root: Path) -> None:
    tuple(path.unlink() for path in attestation_store_dir(root).glob("*.json"))


def _assert_proof(root: Path, head: str, *, selected: Attestation | None = None, gap: str | None = None) -> None:
    (_eq(proof_attestation(root, head), selected), _eq(proof_gaps(root, head), [] if gap is None else [gap]))


def _variant(plan: TransitionPlan, *, policy=None, facts=None, nodes=None, effect=None) -> TransitionPlan:
    policy = policy or dict(plan.policy); facts = facts or Facts.model_validate(plan.facts | {"observed_at": datetime.now(UTC)}); nodes = plan.nodes if nodes is None else nodes  # noqa: E702
    effect = effect or proof_effect_projection(commitment=plan.inputs.commitment, facts=facts.digest(), policy=canonical_json_digest(policy), nodes=nodes)
    return TransitionPlan.compile(inputs=PlanInputs(commitment=plan.inputs.commitment, facts=facts.digest(), prior_attestations=plan.inputs.prior_attestations, policy=canonical_json_digest(policy), effect=canonical_json_digest(effect)), closure={"commitment": plan.commitment, "prior_attestations": plan.prior_attestations, "policy": policy, "effect": effect}, permissions=plan.permissions, facts=facts.model_dump(mode="json", exclude={"observed_at"}), nodes=nodes, verdict=plan.verdict, required_gaps=plan.required_gaps)


def _forge(valid: Attestation, plan: TransitionPlan, *, statement=None, refs=None) -> Attestation:
    payload = valid.model_dump(mode="python", exclude={"id", "schema_version", "statement_digest"}) | {"commitment_digest": plan.inputs.commitment, "facts_digest": plan.inputs.facts, "plan_digest": plan.digest, "policy_digest": plan.inputs.policy, "effect_digest": plan.inputs.effect, "statement": valid.statement | {"plan": plan.model_dump(mode="json"), **(statement or {})}}
    if refs is not None:
        payload["evidence_refs"] = refs
    return Attestation.issue(payload)


def _archive(repo: Path, head: str, changed: tuple[str, ...], authorized: tuple[str, ...]) -> TransitionPlan:
    base = proof_plan(repo, head=head, changed_paths=changed); facts = Facts.model_validate(base.facts | {"observed_at": datetime.now(UTC), "values": base.facts["values"] | {"changed_paths": changed}})  # noqa: E702
    return compile_plan(Commitment.model_validate(dict(base.commitment)), facts, base.nodes, policy=dict(base.policy), prior_attestations={"openspec_archive": {"authorized_paths": list(authorized)}})


def _current_commitment(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    holder = "agent:test:case:current-commitment"; repo = start_adopted_work_lane(root, holder_ref=holder).worktree; lease = proof_module.leases_by_branch(repo)[git(repo, "branch", "--show-current")]; carrier = repo / str(lease["base_commitment_path"]); carrier.write_text(carrier.read_text() + 'acceptance=["current working-tree intent is planned"]\n'); monkeypatch.setenv("ETHOS_ACTOR", holder); plan = proof_plan(repo, head=git(repo, "rev-parse", "HEAD"))  # noqa: E702
    (_eq(plan.inputs.commitment, load_profile_commitment(repo).digest()), _ne(plan.inputs.commitment, lease["base_commitment_digest"]), _eq(plan.commitment["acceptance"], ("current working-tree intent is planned",)))


def _identity_escape(root: Path, _monkeypatch: pytest.MonkeyPatch) -> None:
    repo, head = _repo(root); plan = proof_plan(repo, head=head); carrier = repo / "openspec/changes/proof-binding/commitment.toml"  # noqa: E702
    (_eq(plan.inputs.model_dump(mode="json"), plan.model_dump(mode="json")["inputs"]), _eq(plan.facts["values"]["change_id"], "proof-binding"), _eq(plan.permissions, ("repository.read",)), _raises(TypeError, None, lambda: proof_plan(repo, head=head, expected_commitment_digest="0" * 64)), carrier.write_text(carrier.read_text().replace("repository:self", "repository:foreign")), _eq(proof_plan(repo, head=_commit(repo, "foreign"), change_id="proof-binding").required_gaps, ("repository_subject_mismatch",)))


def _stable_identity(root: Path, _monkeypatch: pytest.MonkeyPatch) -> None:
    repo, head = _repo(root); linked = root / "linked"; first = proof_plan(repo, head=head); subprocess.run(["git", "worktree", "add", "--detach", str(linked), head], cwd=repo, check=True); carrier = repo / "openspec/changes/proof-binding/commitment.toml"; carrier.write_text(carrier.read_text().replace("Bind proof", "Bind revised proof")); changed = proof_plan(repo, head=_commit(repo, "commitment")); (repo / "system").mkdir(exist_ok=True); (repo / "system/gates.toml").write_text("[proof_sets]\ndefault=[]\nfull=[]\n"); policy = proof_plan(repo, head=_commit(repo, "policy"))  # noqa: E702
    (_eq(first.digest, proof_plan(linked, head=head).digest), _eq(len({first.digest, changed.digest, policy.digest}), 3))


def _policy_closure(root: Path, _monkeypatch: pytest.MonkeyPatch) -> None:
    repo = init_git_repo(root); _policy(repo); first_head = _commit(repo, "policy"); first = resolve_gate_policy(repo, tree_ref=first_head); registry = repo / "system/gates.toml"; registry.write_text(registry.read_text().replace("tools/check.sh", "tools/check-v2.sh")); (repo / "tools/check-v2.sh").write_text("#!/bin/sh\nexit 0\n"); changed = resolve_gate_policy(repo, tree_ref=_commit(repo, "command")); (repo / "tools/check-v2.sh").unlink(); missing = _commit(repo, "missing"); (repo / "tools/check-v2.sh").write_text("")  # noqa: E702
    (_eq((tuple(node.id for node in first.nodes), first.gaps), (("check", "publish"), ())), _ne(changed.digest, first.digest), _eq(resolve_gate_policy(repo, tree_ref=missing).gaps, ("gate_policy_source_missing:check:tools/check-v2.sh",)))


def _nox_policy(root: Path, _monkeypatch: pytest.MonkeyPatch) -> None:
    repo = init_git_repo(root); _policy(repo); registry = repo / "system/gates.toml"; registry.write_text(registry.read_text().replace('["tools/check.sh"]', '["{python}","-m","nox","-s","check"]')); tuple((repo / path).write_text(text) for path, text in (("noxfile.py", "def check(): pass\n"), ("pyproject.toml", "[project]\nname='x'\nversion='0'\n"), ("uv.lock", "version=1\n"))); missing = _commit(repo, "nox no runtime"); missing_gaps = resolve_gate_policy(repo, tree_ref=missing).gaps; runtime = repo / ".venv/bin/python"; runtime.parent.mkdir(parents=True); runtime.write_text(""); bound = resolve_gate_policy(repo, tree_ref=_commit(repo, "nox runtime"))  # noqa: E702
    (_eq(missing_gaps, ("gate_runtime_missing:repository-python",)), _eq(bound.gaps, ()), _eq({path for path, _ in bound.sources[0][1]}, {"noxfile.py", "pyproject.toml", "uv.lock"}))


def _policy_semantics(root: Path, _monkeypatch: pytest.MonkeyPatch) -> None:
    repo, _ = _repo(root); profile = repo / ".ethos/profile.toml"; first = resolve_gate_policy(repo, tree_ref=git(repo, "rev-parse", "HEAD")).digest; profile.write_text(profile.read_text().replace('dimensions=["test","coverage"]', 'dimensions=["test","coverage","property"]')); changed = resolve_gate_policy(repo, tree_ref=_commit(repo, "dimensions")); profile.write_text(profile.read_text().replace('static-analysis="sample-static"', 'static-analysis="sample-tests"'))  # noqa: E702
    (_ne(changed.digest, first), _raises(ValueError, "repository_profile_invalid", lambda: resolve_gate_policy(repo, tree_ref=_commit(repo, "invalid map"))), _eq(canonical_gate_command(("/one/bin/python3.14", "-m", "tool")), ("python", "-m", "tool")), _ne(canonical_gate_command(("python3.12", "-m", "tool")), canonical_gate_command(("python3.13", "-m", "tool"))))


def _change_authority(root: Path, _monkeypatch: pytest.MonkeyPatch) -> None:
    repo, _ = _repo(root); second = repo / "openspec/changes/second"; second.mkdir(); (second / "commitment.toml").write_text('schema_version=1\nid="change:second"\nintent="Second"\nsubjects=["repository:self"]\nscope=["**"]\n'); head = _commit(repo, "second"); _raises(ValueError, "commitment_ambiguous", lambda: proof_plan(repo, head=head)); selected = proof_plan(repo, head=head, change_id="proof-binding"); (second / "tasks.md").write_text("- [x] Done\n"); (repo / "openspec/changes/proof-binding/tasks.md").write_text("- [x] Complete\n"); complete = _commit(repo, "complete")  # noqa: E702
    (_eq(selected.facts["values"]["change_id"], "proof-binding"), _raises(ValueError, "commitment_ambiguous", lambda: proof_plan(repo, head=complete)), _ne(proof_plan(repo, head=complete, change_id="proof-binding").inputs.commitment, load_repository_commitment(repo, tree_ref=complete).digest()))


def _exact_binding(root: Path, _monkeypatch: pytest.MonkeyPatch) -> None:
    repo, head = _repo(root); plan = proof_plan(repo, head=head); record = _issue(repo, head); path = persist_proof_attestation(repo, record); artifact = record.statement["artifact"]; _true(isinstance(artifact, Mapping)); digest = str(artifact["sha256"]).removeprefix("sha256:")  # noqa: E702
    (_eq(path, attestation_store_dir(repo) / f"{record.id}.json"), _eq(path.read_text(), record.canonical_json()), _eq((record.predicate, record.subject, record.verdict), ("proof:execution", f"git:commit:{head}", "pass")), _eq((record.commitment_digest, record.facts_digest, record.plan_digest, record.policy_digest), (plan.inputs.commitment, plan.inputs.facts, plan.digest, plan.inputs.policy)), _eq(record.effect_digest, plan.inputs.effect), _ne(plan.inputs.effect, digest), _eq(record.evidence_refs, (f"sha256:{digest}",)), _eq(record.valid_from, record.issued_at), _eq(mutable_json(record.statement["plan"]), plan.model_dump(mode="json")), _eq(set(record.statement), {"artifact", "boundary", "claim", "context", "plan", "plane", "required_gaps", "scope"}), _assert_proof(repo, head, selected=record))


def _projection_divergence(root: Path, _monkeypatch: pytest.MonkeyPatch) -> None:
    repo, head = _repo(root); plan = proof_plan(repo, head=head)  # noqa: E702
    tuple(_raises(ValueError, "transition_plan_policy_node_mismatch", lambda policy=(dict(plan.policy) | {"gates" if drift == "nodes" else "gaps": list(plan.policy["gates"][:-1]) if drift == "nodes" else ["gate_policy_source_missing:sample-tests"]}): _variant(plan, policy=policy)) for drift in ("nodes", "gaps"))


def _predicate_drift(root: Path, _monkeypatch: pytest.MonkeyPatch) -> None:
    repo, head = _repo(root); valid = _issue(repo, head); rows = (("claim", {"objective": "other", "verdict": "block"}, "proof_attestation_claim_mismatch"), ("scope", [], "proof_attestation_scope_mismatch"), ("plane", "hosted", "proof_attestation_plane_mismatch"), ("context", {}, "proof_attestation_context_mismatch"), ("boundary", "other", "proof_attestation_boundary_mismatch"))  # noqa: E702
    tuple((_clear(repo), _store(repo, _reissue(valid, statement=valid.statement | {field: value})), _assert_proof(repo, head, gap=gap)) for field, value, gap in rows)


def _model_policy_drift(root: Path, _monkeypatch: pytest.MonkeyPatch) -> None:
    repo, head = _repo(root); valid = _issue(repo, head); persist_proof_attestation(repo, valid); _store(repo, _reissue(valid, statement=valid.statement | {"novel_semantics": True})); _assert_proof(repo, head, gap="model_gap"); fresh, fresh_head = _repo(root.parent / "fresh"); persist_proof_attestation(fresh, _issue(fresh, fresh_head)); profile = fresh / ".ethos/profile.toml"; profile.write_text(profile.read_text().replace('["sample","typecheck"]', '["sample","typecheck","--strict"]'))  # noqa: E702
    _assert_proof(fresh, _commit(fresh, "policy drift"), gap="proof_not_proven")


def _model_facts_stale(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo, head = _repo(root); plan = proof_plan(repo, head=head); fact = Facts.model_validate(plan.facts | {"observed_at": datetime.now(UTC), "values": plan.facts["values"] | {"novel": True}}); _raises(ValueError, "transition_plan_model_gap", lambda: _variant(plan, facts=fact)); monkeypatch.setattr(proof_module, "current_tree", lambda *_args, **_kwargs: "0" * 40)  # noqa: E702
    _raises(ValueError, "proof_attestation_live_facts_stale", lambda: _issue(repo, head, plan=plan, issued_at=None))


def _head_subject_stale(root: Path, _monkeypatch: pytest.MonkeyPatch) -> None:
    repo, first = _repo(root); plan = proof_plan(repo, head=first); (repo / "DRIFT.md").write_text("drift\n"); _commit(repo, "move head"); _raises(ValueError, "proof_attestation_live_facts_stale", lambda: _issue(repo, first, plan=plan, issued_at=None)); second = git(repo, "commit-tree", "HEAD^{tree}", "-p", git(repo, "rev-parse", "HEAD"), "-m", "empty"); git(repo, "update-ref", "refs/heads/dev", second); record = _issue(repo, second); artifact = write_proof_artifact(attestation_store_dir(repo), first, _checks(repo, second)); digest = str(artifact["sha256"]).removeprefix("sha256:"); forged = _reissue(record, subject=f"git:commit:{first}", statement=record.statement | {"head": first, "artifact": artifact}, effect_digest=digest, evidence_refs=(f"sha256:{digest}",)); _store(repo, forged)  # noqa: E702
    _eq(proof_gaps(repo, first), ["proof_attestation_plan_head_mismatch"])


def _query_legacy_tamper(root: Path, _monkeypatch: pytest.MonkeyPatch) -> None:
    repo, head = _repo(root); focused = _issue(repo, head, boundary="focused"); persist_proof_attestation(repo, focused); _assert_proof(repo, head, gap="proof_attestation_context_mismatch"); store = attestation_store_dir(repo); rows = ((_reissue(_issue(repo, head), predicate="experiment:novel"), "proof_not_proven"), (_reissue(_issue(repo, head), plan_digest="0" * 64), "proof_attestation_binding_mismatch:plan_digest")); tuple((_clear(repo), _store(repo, record), _assert_proof(repo, head, gap=gap)) for record, gap in rows); legacy = repo / ".ethos/state/proof" / f"{head}.json"; legacy.parent.mkdir(parents=True, exist_ok=True); legacy.write_text(json.dumps({"schema_version": 4, "head": head, "state": "proven"})); _clear(repo); _assert_proof(repo, head, gap="proof_not_proven"); valid = _issue(repo, head); persist_proof_attestation(repo, valid); artifact = valid.statement["artifact"]; _true(isinstance(artifact, Mapping)); (store / str(artifact["path"])).write_text("tampered")  # noqa: E702
    _assert_proof(repo, head, gap="proof_attestation_artifact_digest_mismatch")


def _persistence_closure(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo, head = _repo(root); record = _issue(repo, head); path = persist_proof_attestation(repo, record); _eq(persist_proof_attestation(repo, record), path); monkeypatch.setattr(proof_module, "load_profile_commitment", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError())); monkeypatch.setattr(proof_module, "load_repository_commitment", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError())); _assert_proof(repo, head, selected=record); path.write_text("{}")  # noqa: E702
    _raises(ValueError, "attestation_identity_collision", lambda: persist_proof_attestation(repo, record))


def _scope_effect_policy(root: Path, _monkeypatch: pytest.MonkeyPatch) -> None:
    repo, head = _repo(root); plan = proof_plan(repo, head=head, changed_paths=("src/feature.py",)); arbitrary = {"operation": "arbitrary"}; _raises(ValueError, "transition_plan_effect_mismatch", lambda: TransitionPlan.compile(inputs=plan.inputs.model_copy(update={"effect": canonical_json_digest(arbitrary)}), closure={"commitment": plan.commitment, "prior_attestations": plan.prior_attestations, "policy": plan.policy, "effect": arbitrary}, permissions=plan.permissions, facts=plan.facts, nodes=plan.nodes)); commitment = dict(plan.commitment) | {"scope": ["docs/**"]}; digest = canonical_json_digest(commitment); effect = proof_effect_projection(commitment=digest, facts=plan.inputs.facts, policy=plan.inputs.policy, nodes=plan.nodes); _raises(ValueError, "transition_plan_semantics_mismatch", lambda: TransitionPlan.compile(inputs=PlanInputs(commitment=digest, facts=plan.inputs.facts, policy=plan.inputs.policy, effect=canonical_json_digest(effect)), closure={"commitment": commitment, "prior_attestations": plan.prior_attestations, "policy": plan.policy, "effect": effect}, permissions=tuple(commitment["permissions"]), facts=plan.facts, nodes=plan.nodes)); policy = dict(plan.policy) | {"noncanonical": True}; _store(repo, _forge(_issue(repo, head), _variant(plan, policy=policy)))  # noqa: E702
    _assert_proof(repo, head, gap="proof_attestation_repository_policy_mismatch")


def _gate_tree_negative(root: Path, _monkeypatch: pytest.MonkeyPatch) -> None:
    repo, head = _repo(root); valid = _issue(repo, head); plan = proof_plan(repo, head=head); nodes = plan.nodes[:-1]; policy = dict(plan.policy); policy["gates"] = list(policy["gates"][:-1]); values = dict(plan.facts["values"]) | {"gate_ids": [node.id for node in nodes]}; facts = Facts(repository=str(plan.facts["repository"]), head=head, tree=str(plan.facts["tree"]), observed_at=datetime.now(UTC), values=values, source_refs=tuple(plan.facts["source_refs"])); forged_plan = _variant(plan, policy=policy, facts=facts, nodes=nodes); checks = _checks(repo, head)[:-1]; artifact = write_proof_artifact(attestation_store_dir(repo), head, checks); digest = str(artifact["sha256"]).removeprefix("sha256:"); _store(repo, _forge(valid, forged_plan, statement={"artifact": artifact}, refs=(f"sha256:{digest}",))); _assert_proof(repo, head, gap="proof_attestation_repository_policy_mismatch"); _clear(repo); nonexistent = Facts.model_validate(plan.facts | {"observed_at": datetime.now(UTC), "tree": "0" * 40}); _store(repo, _forge(valid, _variant(plan, facts=nonexistent)))  # noqa: E702
    _assert_proof(repo, head, gap="proof_attestation_live_tree_mismatch")


def _full_floor(root: Path, _monkeypatch: pytest.MonkeyPatch) -> None:
    repo = init_git_repo(root); _policy(repo, full=True); (repo / ".ethos/commitment.toml").write_text('schema_version=1\nid="repository:repo"\nintent="govern"\nsubjects=["repository:repo"]\nscope=["**"]\n'); carrier = repo / "openspec/changes/proof-binding"; carrier.mkdir(parents=True); (carrier / "commitment.toml").write_text('schema_version=1\nid="change:proof-binding"\nintent="proof"\nsubjects=["repository:self"]\nscope=["**"]\n'); head = _commit(repo, "full floor"); default = _issue(repo, head); persist_proof_attestation(repo, default); _assert_proof(repo, head, gap="full_proof_required"); plan = proof_plan(repo, head=head, full=True); full = _issue(repo, head, plan=plan, checks=_checks(repo, head, full=True)); persist_proof_attestation(repo, full)  # noqa: E702
    (_ne(default.plan_digest, full.plan_digest), _assert_proof(repo, head, selected=full))


def _equivalent_conflict(root: Path, _monkeypatch: pytest.MonkeyPatch) -> None:
    repo, head = _repo(root); first = _issue(repo, head); persist_proof_attestation(repo, first); later = _reissue(first, issued_at=first.issued_at + timedelta(seconds=1)); persist_proof_attestation(repo, later); _eq(proof_attestation(repo, head).id, min(first.id, later.id)); conflict = _reissue(first, verifier="agent:test:case:conflict", statement=first.statement | {"claim": {"objective": "conflict", "verdict": "pass"}}); persist_proof_attestation(repo, conflict)  # noqa: E702
    _assert_proof(repo, head, gap="contradiction")


def _equivalent_artifacts(root: Path, _monkeypatch: pytest.MonkeyPatch) -> None:
    repo, head = _repo(root); first = _issue(repo, head); persist_proof_attestation(repo, first); checks = tuple(check | {"stdout": f"{check['stdout']} again"} for check in _checks(repo, head)); second = _issue(repo, head, checks=checks, issued_at=first.issued_at + timedelta(seconds=1)); persist_proof_attestation(repo, second)  # noqa: E702
    (_eq(first.effect_digest, second.effect_digest), _ne(first.evidence_refs, second.evidence_refs), _true(proof_attestation(repo, head) is not None), _eq(proof_gaps(repo, head), []))


def _archive_authority(root: Path, _monkeypatch: pytest.MonkeyPatch) -> None:
    repo, head = _repo(root); historical = _issue(repo, head, plan=_archive(repo, head, ("historical.py", "current.py"), ("current.py",))); persist_proof_attestation(repo, historical); _assert_proof(repo, head, gap="proof_archive_scope_stale"); current = _issue(repo, head, plan=_archive(repo, head, ("current.py",), ("current.py",))); persist_proof_attestation(repo, current)  # noqa: E702
    _assert_proof(repo, head, selected=current)


def _expired_foreign(root: Path, _monkeypatch: pytest.MonkeyPatch) -> None:
    repo, head = _repo(root); current = _issue(repo, head); persist_proof_attestation(repo, current); issued = datetime.now(UTC) - timedelta(minutes=2)  # noqa: E702
    tuple((_store(repo, _reissue(current, issued_at=issued, valid_from=issued, valid_until=issued + timedelta(minutes=1), **({"statement": current.statement | {"novel_semantics": True}} if novel else {}))), _assert_proof(repo, head, selected=current)) for novel in (False, True)); _store(repo, _reissue(current, statement=current.statement | {"scope": ("workspace",)})); _assert_proof(repo, head, selected=current)  # noqa: E702


def _policy_artifact_drift(root: Path, _monkeypatch: pytest.MonkeyPatch) -> None:
    repo, head = _repo(root); valid = _issue(repo, head); persist_proof_attestation(repo, valid); _store(repo, _reissue(valid, policy_digest="0" * 64)); _assert_proof(repo, head, gap="proof_policy_digest_stale"); descriptor = valid.statement["artifact"]; _true(isinstance(descriptor, Mapping)); forged = _reissue(valid, statement=valid.statement | {"artifact": descriptor | {"media_type": "text/plain", "extra": "unbound"}})  # noqa: E702
    _eq(artifact_checks(attestation_store_dir(repo), forged)[1], ["proof_attestation_artifact_binding_mismatch"])


CLAIM_MATRIX = [
    pytest.param(_current_commitment, id="test_work_lane_proof_plan_uses_the_current_active_commitment->plan/current-active-commitment"),
    pytest.param(_identity_escape, id="test_proof_plan_binds_identity_and_rejects_escape_hatches->plan/identity-and-escape-hatches"),
    pytest.param(_stable_identity, id="test_proof_plan_identity_is_stable_across_worktrees_and_changes_with_inputs->plan/worktree-stability-and-input-sensitivity"),
    pytest.param(_policy_closure, id="test_gate_policy_closure_sources_runtime_and_semantics->policy/source-closure-and-missing-source"),
    pytest.param(_nox_policy, id="test_nox_policy_binds_repository_sources_and_fails_without_runtime->policy/nox-source-binding-and-runtime-floor"),
    pytest.param(_policy_semantics, id="test_gate_policy_order_profile_semantics_and_python_command_normalization->policy/profile-semantics-and-command-normalization"),
    pytest.param(_change_authority, id="test_change_selection_preserves_unarchived_authority->authority/unarchived-change-selection"),
    pytest.param(_exact_binding, id="test_proof_attestation_is_content_addressed_and_exactly_bound->attestation/content-addressed-semantic-closure"),
    pytest.param(_projection_divergence, id="test_transition_plan_rejects_policy_projection_divergence->plan/policy-projection-divergence[nodes|gaps]"),
    pytest.param(_predicate_drift, id="test_proof_predicate_evidence_drift_fails_closed->negative/predicate-evidence-drift[claim|scope|plane|context|boundary]"),
    pytest.param(_model_policy_drift, id="test_unmappable_facts_and_live_policy_drift_fail_closed->negative/model-gap-and-live-policy-drift"),
    pytest.param(_model_facts_stale, id="test_plan_model_gap_and_live_facts_drift_block_issuance->negative/model-gap-and-live-facts-stale"),
    pytest.param(_head_subject_stale, id="test_head_and_subject_relabel_drift_fail_closed->negative/head-stale-and-subject-relabel"),
    pytest.param(_query_legacy_tamper, id="test_query_predicate_legacy_artifact_and_binding_fail_closed->negative/query-predicate-legacy-binding-tamper"),
    pytest.param(_persistence_closure, id="test_persistence_identity_and_self_contained_closure->attestation/persistence-identity-and-self-contained-closure"),
    pytest.param(_scope_effect_policy, id="test_self_consistent_scope_effect_and_policy_bypasses_fail_closed->negative/effect-scope-policy-bypass"),
    pytest.param(_gate_tree_negative, id="test_gate_omission_and_nonexistent_tree_fail_closed->negative/gate-omission-and-live-tree"),
    pytest.param(_full_floor, id="test_repository_admission_prefers_full_proof->authority/full-proof-floor"),
    pytest.param(_equivalent_conflict, id="test_equivalent_proofs_supersede_deterministically_but_conflicts_block->authority/equivalent-supersession-and-contradiction"),
    pytest.param(_equivalent_artifacts, id="test_equivalent_proofs_with_different_artifacts_share_closure->attestation/artifact-independent-semantic-closure"),
    pytest.param(_archive_authority, id="test_archive_authority_supersedes_historical_scope_and_requires_current_proof->authority/archive-current-scope"),
    pytest.param(_expired_foreign, id="test_expired_or_other_query_proofs_do_not_pollute_current_authority->authority/expired-or-foreign-query[known|novel]"),
    pytest.param(_policy_artifact_drift, id="test_policy_binding_and_artifact_descriptor_drift_fail_closed->negative/policy-stale-and-artifact-descriptor-tamper"),
]


@pytest.mark.parametrize("claim", CLAIM_MATRIX)
def test_proof_plan_claim_state_matrix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, claim) -> None:
    claim(tmp_path / "repo", monkeypatch)
