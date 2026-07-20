from __future__ import annotations

from pathlib import Path

import pytest

import ethos.adapters.admission.control.replacement as repl
import ethos.adapters.mutation.core as mutation
import ethos.adapters.mutation.proof as proof
import ethos.surface.cli._gate_runner as gate_cli
import ethos.surface.cli.hook.core as hook_cli
import ethos.surface.cli.root.lifecycle as life
from ethos.adapters.mutation.closeout import core as closeout
from ethos_core.action_graph.core import ActionNode
from ethos_core.contracts.branch.roles import BranchRolePolicy
from ethos_core.contracts.lifecycle.core import MutationEvaluation
from tests.support.subprocesses import completed as cp


def _patch(monkeypatch: pytest.MonkeyPatch, target: object, **values: object) -> None:
    for name, value in values.items():
        monkeypatch.setattr(target, name, value)


def _runner(*results: object):
    iterator = iter(results)
    return lambda *_args, **_kwargs: next(iterator)


def _request(root: Path, policy: BranchRolePolicy | None = None, worktrees: list[dict[str, object]] | None = None) -> closeout.CloseoutRequest:  # fmt: skip
    return closeout.CloseoutRequest(root, policy or BranchRolePolicy(), "old", "new", root, worktrees or [])  # fmt: skip


def _run(root: Path, monkeypatch: pytest.MonkeyPatch, statuses: tuple[str, ...], reports: tuple[dict[str, object], ...]):  # fmt: skip
    status_iter, report_iter = iter(statuses), iter(reports)
    audits, controls, emitted, events = [], [], [], []

    def audit(*_args: object, current_head: str = "") -> dict[str, object]:
        events.append("audit")
        audits.append(current_head)
        return {"ok": True, "required_gaps": [], "governance_context": {}}

    def status(*_args: object, **_kwargs: object) -> dict[str, object]:
        events.append("status")
        return {"candidate": {"head": next(status_iter)}}

    def control(**values: object) -> dict[str, object]:
        events.append("control")
        controls.append(str(values["candidate_head"]))
        return next(report_iter)

    _patch(monkeypatch, life, resolve_root=lambda _root: root, evaluate_closeout_mutation=lambda *_args, **_kwargs: MutationEvaluation(ok=True, state="ready"), completed_active_changes_report=lambda _root: {"ok": True, "required_gaps": []}, workspace_status=status, control_replacement_report=control, apply_candidate_to_accepted=lambda **_kwargs: pytest.fail("effect after failed recheck"), emit=lambda result, **_kwargs: emitted.append(result), _closeout_result=lambda payload: payload)  # fmt: skip
    _patch(monkeypatch, life.git, current_head=lambda _root: "a" * 40)
    _patch(monkeypatch, life.land_core, closeout_audit_root=lambda *_args: root, repository_audit_after_admission=audit)  # fmt: skip
    life.land(apply=True, authorize=True, expect_head="a" * 40, closeout=True, root=root, json_output=True)  # fmt: skip
    return emitted[0], controls, audits, events


def test_closeout_rechecks_and_ref_failures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:  # fmt: skip
    allow = {"verdict": "allow", "required_gaps": []}
    defer = {"verdict": "defer", "required_gaps": ["fresh_control_gap"]}
    result, _, audits, events = _run(tmp_path, monkeypatch, ("b" * 40,) * 3, (allow, defer))
    assert (result.ok, result.gaps, audits, events[:2]) == (False, ("fresh_control_gap",), ["b" * 40], ["status", "audit"])  # fmt: skip
    result, controls, audits, events = _run(tmp_path, monkeypatch, ("b" * 40, "c" * 40), (allow,))
    assert (result.ok, result.gaps, controls, audits, events[:2]) == (False, ("candidate_head_changed_after_closeout_audit",), [], ["b" * 40], ["status", "audit"])  # fmt: skip
    request = closeout.CloseoutRequest(tmp_path, BranchRolePolicy(), "h1", "c2", tmp_path, [])
    accepted = closeout.CloseoutTransition("refs/heads/dev", "h1", "c2", "c2")
    classify = closeout._ref_transaction_failure  # noqa: SLF001, RUF100 - ref failure edge
    for accepted_now, candidate_now, gap in (("h2", "c2", "accepted_advanced_concurrently"), ("h1", "c3", "candidate_head_changed_after_control_replacement_check"), ("h1", "c2", "accepted_atomic_update_rejected")):  # fmt: skip

        def observe(_root: Path, *args: str, accepted_now: str = accepted_now, candidate_now: str = candidate_now, **_kwargs: object):  # fmt: skip
            return cp(accepted_now if args[-1] == accepted.ref_name else candidate_now)

        report = classify(request, accepted, cp(stderr="transaction rejected", returncode=1), observe)  # fmt: skip
        assert (report["required_gaps"], report["stderr"]) == ([gap], "transaction rejected")


def test_control_replacement_failure_edges(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    changed, receipt, receipt_gaps, snapshot, artifacts = repl._changed_paths, repl._external_receipt, repl._receipt_gaps, repl._control_snapshot_gaps, repl._external_artifacts  # noqa: SLF001, RUF100 - receipt edges  # fmt: skip
    proof_gaps, decision_gaps, proof_head, digest = repl._candidate_proof_gaps, repl._bootstrap_decision_gaps, repl._native_executed_proof_head, repl._control_digest  # noqa: SLF001, RUF100 - proof edges  # fmt: skip
    monkeypatch.setattr(repl.subprocess, "run", lambda *_args, **_kwargs: cp(returncode=1))
    assert changed(tmp_path, "a", "b") is None
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    inside, missing, invalid = candidate / "receipt", tmp_path / "missing", tmp_path / "invalid"
    inside.write_text("{}", encoding="utf-8")
    invalid.write_text("[]", encoding="utf-8")
    args = {"accepted_head": "a", "candidate_head": "b", "candidate_root": candidate}
    assert [receipt(path=path, **args)[1] for path in (inside, missing, invalid)] == [["bootstrap_verifier_inside_candidate_tree"], ["control_replacement_receipt_invalid"], ["control_replacement_receipt_invalid"]]  # fmt: skip
    with monkeypatch.context() as patch:
        _patch(patch, repl, validate_schema_instance=lambda *_args, **_kwargs: {"ok": True}, _control_snapshot_gaps=lambda *_args, **_kwargs: [], _candidate_proof_gaps=lambda *_args, **_kwargs: [])  # fmt: skip
        for data, expected in (({}, {"control_replacement_control_paths_mismatch"}), ({"bootstrap_decision_path": b"{"}, {"control_replacement_control_paths_mismatch", "control_replacement_bootstrap_decision_invalid"})):  # fmt: skip
            patch.setattr(repl, "_external_artifacts", lambda *_args, data=data, **_kwargs: (data, []))  # fmt: skip
            assert expected <= set(receipt_gaps({}, control_paths=(), **args))
        gaps = receipt_gaps({}, **args)
        assert ("control_replacement_bootstrap_decision_invalid" in gaps, "control_replacement_control_paths_mismatch" in gaps) == (True, False)  # fmt: skip
    with monkeypatch.context() as patch:
        patch.setattr(repl, "_control_digest", lambda *_args: None)
        assert snapshot({}, root=candidate, accepted_head="a", candidate_head="b", control_paths=("x",)) == ["control_replacement_control_snapshot_unavailable"]  # fmt: skip
    verifier, decision = tmp_path / "verifier", tmp_path / "decision"
    verifier.write_bytes(b"x")
    decision.write_bytes(b"x")
    external = {"verifier_path": str(verifier), "bootstrap_decision_path": str(decision)}
    inside_data = {"verifier_path": str(candidate), "bootstrap_decision_path": str(candidate)}
    missing_data = {"verifier_path": str(missing), "bootstrap_decision_path": str(missing)}
    expected_inside = ["bootstrap_verifier_inside_candidate_tree", "bootstrap_decision_inside_candidate_tree"]  # fmt: skip
    expected_missing = ["control_replacement_verifier_missing", "bootstrap_decision_missing"]
    assert [artifacts(data, candidate)[1] for data in (inside_data, missing_data)] == [expected_inside, expected_missing]  # fmt: skip
    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_bytes", lambda _path: (_ for _ in ()).throw(OSError))
        assert artifacts(external, candidate)[1] == expected_missing
        assert proof_gaps({"candidate_proof_path": str(verifier)}, candidate, "h") == ["control_replacement_candidate_proof_not_proven"]  # fmt: skip
    assert artifacts(external, candidate)[1] == ["control_replacement_verifier_digest_mismatch", "bootstrap_decision_digest_mismatch"]  # fmt: skip
    assert [proof_gaps({"candidate_proof_path": str(path)}, candidate, "h") for path in (candidate, missing)] == [["control_replacement_candidate_proof_inside_candidate_tree"], ["control_replacement_candidate_proof_missing"]]  # fmt: skip
    verifier.write_bytes(b"{")
    assert proof_gaps({"candidate_proof_path": str(verifier), "candidate_proof_digest": "bad"}, candidate, "h") == ["control_replacement_candidate_proof_digest_mismatch", "control_replacement_candidate_proof_not_proven"]  # fmt: skip
    assert decision_gaps([], receipt={}, accepted_head="a", candidate_head="b") == ["control_replacement_bootstrap_decision_invalid"]  # fmt: skip
    invalid_proofs = ({"command": "prove", "ok": True, "state": "proven", "data": []}, {"command": "prove", "ok": True, "state": "proven", "data": {"executed": True, "provenance": {}, "evidence": []}})  # fmt: skip
    assert [proof_head(value) for value in invalid_proofs] == ["", ""]
    for run in (_runner(cp(returncode=1)), _runner(cp(stdout=b"x"), cp(returncode=1))):
        monkeypatch.setattr(repl.subprocess, "run", run)
        assert digest(candidate, "h", ("x",)) is None


def test_mutation_and_closeout_failure_edges(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:  # fmt: skip
    runs_head, merge_key, proof_path = proof._runs_prove_head, proof._run_merge_key, proof._proof_path  # noqa: SLF001, RUF100 - proof edges  # fmt: skip
    assert (runs_head([]), [merge_key(value, 4) for value in ({"id": "x"}, {})]) == (False, ["legacy:x", "index:4"])  # fmt: skip
    monkeypatch.setattr(proof, "executed_proof_record", lambda *_args: None)
    assert (proof.carry_executed_proof_record(source_root=tmp_path, target_root=tmp_path / "t", head="h")["state"], proof.discard_executed_proof(tmp_path, "h")) == ("skipped", False)  # fmt: skip
    path = proof_path(tmp_path, "h")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x", encoding="utf-8")
    assert proof.discard_executed_proof(tmp_path, "h") is True
    policy = BranchRolePolicy()
    _patch(monkeypatch, mutation, load_branch_role_policy=lambda _root: policy, run_git=lambda _root, *args, **_kwargs: cp("h") if args[0] == "rev-parse" else cp(stderr="merge", returncode=1), candidate_base_report=lambda **_kwargs: {"ok": True, "path": str(tmp_path)}, carry_executed_proof_record=lambda **_kwargs: {"ok": True})  # fmt: skip
    discarded: list[object] = []
    monkeypatch.setattr(mutation, "discard_executed_proof", lambda *values: discarded.append(values))  # fmt: skip
    report = mutation.apply_land_to_candidate(root=tmp_path, authorized=True, expect_head="h", admitted_decision=MutationEvaluation(ok=True, state="ready"))  # fmt: skip
    assert (report["required_gaps"], bool(discarded)) == (["candidate_update_failed"], True)
    _patch(monkeypatch, mutation, run_git=lambda *_args, **_kwargs: cp("h"), evaluate_closeout_mutation=lambda *_args, **_kwargs: MutationEvaluation(ok=True, state="ready"), workspace_status=lambda *_args, **_kwargs: {"candidate": {"head": "new"}})  # fmt: skip
    assert mutation.apply_candidate_to_accepted(root=tmp_path, authorized=True, expect_head="h", candidate_head="old")["required_gaps"] == ["candidate_head_changed_after_control_replacement_check"]  # fmt: skip
    request = _request(tmp_path)
    assert closeout.promote_candidate_to_accepted(request, dependencies=closeout.CloseoutDependencies(is_ancestor=lambda *_args: False))["required_gaps"] == ["candidate_diverged_from_accepted"]  # fmt: skip
    mirror = BranchRolePolicy(release_mirror="accepted_ff")
    preflight = closeout._promotion_preflight  # noqa: SLF001, RUF100 - preflight edge
    for old, ahead, gap in (("", False, "release_mirror_release_branch_missing"), ("r", True, "release_mirror_ahead_of_accepted"), ("r", False, "release_mirror_diverged")):  # fmt: skip

        def ancestor(_root: Path, left: str, right: str, *, ahead: bool = ahead) -> bool:
            return True if (left, right) == ("old", "new") else ahead if (left, right) == ("old", "r") else False  # fmt: skip

        deps = closeout.CloseoutDependencies(run_git=lambda *_args, old=old, **_kwargs: cp(old), is_ancestor=ancestor)  # fmt: skip
        assert preflight(_request(tmp_path, mirror), deps)["required_gaps"] == [gap]
    accepted = closeout.CloseoutTransition("refs/heads/dev", "old", "new", "new")
    execute = closeout._execute_promotion  # noqa: SLF001, RUF100 - promotion edge
    monkeypatch.setattr(closeout, "sweep_stale_closeout_intents", lambda *_args: None)
    assert execute(request, (accepted, None, ""), closeout.CloseoutDependencies(carry_proof=lambda **_kwargs: None))["required_gaps"] == ["proof_invalid"]  # fmt: skip
    _patch(monkeypatch, closeout, _proof_digest=lambda *_args: "d", gate_policy_digest=lambda *_args, **_kwargs: "p", _hook_bootstrap_required=lambda *_args: False)  # fmt: skip
    okdeps = closeout.CloseoutDependencies(carry_proof=lambda **_kwargs: {"ok": True})
    with monkeypatch.context() as patch:
        patch.setattr(closeout, "_advance_and_sync_accepted", lambda *_args: {"required_gaps": ["sync"]})  # fmt: skip
        assert execute(request, (accepted, None, ""), okdeps)["required_gaps"] == ["sync"]
    release = closeout.CloseoutTransition("refs/heads/main", "r", "new", "new")
    with monkeypatch.context() as patch:
        _patch(patch, closeout, _hook_bootstrap_required=lambda *_args: True, _advance_and_sync_accepted=lambda *_args: 1, _write_intents=lambda *_args: [], _clear_intents=lambda *_args: None, _ref_transaction=lambda *_args, **_kwargs: cp(stderr="no", returncode=1))  # fmt: skip
        assert execute(_request(tmp_path, mirror), (accepted, release, "r"), okdeps)["required_gaps"] == ["release_mirror_bootstrap_incomplete"]  # fmt: skip
    trees = [{"branch": "main", "path": str(tmp_path), "worktree_binding": "linked"}]
    mirror_request = _request(tmp_path, mirror, trees)
    for run, gap in ((_runner(cp(stderr="sync", returncode=1)), "release_mirror_worktree_sync_failed"), (_runner(cp(), cp(stdout="M")), "release_mirror_worktree_dirty_after_sync")):  # fmt: skip
        with monkeypatch.context() as patch:
            patch.setattr(closeout, "_advance_and_sync_accepted", lambda *_args: 1)
            deps = closeout.CloseoutDependencies(run_git=run, carry_proof=lambda **_kwargs: {"ok": True})  # fmt: skip
            assert execute(mirror_request, (accepted, release, "r"), deps)["required_gaps"] == [gap]


def test_sync_cli_and_hook_edges(  # noqa: PLR0915, RUF100 - related closeout edge matrix
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = _request(tmp_path)
    accepted = closeout.CloseoutTransition("refs/heads/dev", "old", "new", "new")
    advance = closeout._advance_and_sync_accepted  # noqa: SLF001, RUF100 - sync edge
    common = {"request": request, "transitions": (accepted,), "evidence_digest": "d", "policy_digest": "p"}  # fmt: skip
    with monkeypatch.context() as patch:
        _patch(patch, closeout, _write_intents=lambda *_args: [], _clear_intents=lambda *_args: None, _ref_transaction=lambda *_args, **_kwargs: cp(stderr="reject", returncode=1))  # fmt: skip
        deps = closeout.CloseoutDependencies(run_git=lambda _root, *args, **_kwargs: cp("old" if args[-1] == accepted.ref_name else "new"), discard_proof=lambda *_args: None)  # fmt: skip
        assert advance(dependencies=deps, **common)["required_gaps"] == ["accepted_atomic_update_rejected"]  # fmt: skip
    for synced, status, gap in ((cp(stderr="sync", returncode=1), cp(), "accepted_worktree_sync_failed"), (cp(), cp(stdout="M"), "accepted_worktree_dirty_after_sync")):  # fmt: skip
        with monkeypatch.context() as patch:
            _patch(patch, closeout, _write_intents=lambda *_args: [], _clear_intents=lambda *_args: None, _ref_transaction=lambda *_args, **_kwargs: cp(), _sync=lambda *_args, synced=synced: (synced, 1))  # fmt: skip
            deps = closeout.CloseoutDependencies(run_git=lambda *_args, status=status, **_kwargs: status)  # fmt: skip
            assert advance(dependencies=deps, **common)["required_gaps"] == [gap]
    assert (closeout.proof_required_gaps(None), closeout.proof_carry_failure(request, None)["required_gaps"]) == (["proof_invalid"], ["proof_invalid"])  # fmt: skip
    sync = closeout._sync  # noqa: SLF001, RUF100 - retry edge
    assert sync(tmp_path, "h", _runner(cp(stderr="index.lock", returncode=1), cp()))[1] == 2
    release = closeout.CloseoutTransition("refs/heads/main", "old", "new", "new")
    trees = [{"branch": "main", "path": str(tmp_path), "worktree_binding": "linked"}]
    assert [closeout.sync_release_mirror(release, trees, "new", "old", run)["worktree_sync"] for run in (lambda *_args, **_kwargs: cp(stderr="no", returncode=1), _runner(cp(), cp(stdout="M")))] == ["failed", "dirty"]  # fmt: skip

    def node(*command: str) -> ActionNode:
        return ActionNode("x", "gate", command)

    assert [gate_cli.run_inprocess_cli_gate(value, tmp_path) for value in (node("ethos", "status"), node("python", "x", "--json"))] == [None, None]  # fmt: skip
    with monkeypatch.context() as patch:
        _patch(patch, gate_cli, _current_cwd=lambda: None, _restore_cwd=lambda *_args: None, load_command_groups=lambda *_args: None, app=lambda *_args, **_kwargs: None)  # fmt: skip
        patch.setattr(gate_cli.os, "chdir", lambda *_args: None)
        assert gate_cli.run_inprocess_cli_gate(node("ethos", "status", "--json"), tmp_path).exit_code == 1  # fmt: skip
    with monkeypatch.context() as patch:
        _patch(patch, gate_cli, _current_cwd=lambda: tmp_path, _restore_cwd=lambda *_args: None, load_command_groups=lambda *_args: None, app=lambda *_args, **_kwargs: (_ for _ in ()).throw(SystemExit("x")))  # fmt: skip
        patch.setattr(gate_cli.os, "chdir", lambda *_args: None)
        assert gate_cli.run_inprocess_cli_gate(node("ethos", "status", "--json"), tmp_path).exit_code == 1  # fmt: skip
    with monkeypatch.context() as patch:
        patch.setattr(gate_cli.Path, "cwd", lambda: (_ for _ in ()).throw(OSError))
        assert gate_cli._current_cwd() is None  # noqa: SLF001, RUF100 - cwd edge
    attempts: list[Path] = []

    def chdir(path: Path) -> None:
        attempts.append(path)
        if path != Path("/"):
            raise OSError

    monkeypatch.setattr(gate_cli.os, "chdir", chdir)
    gate_cli._restore_cwd(tmp_path / "gone", tmp_path)  # noqa: SLF001, RUF100 - fallback edge
    assert attempts == [tmp_path / "gone", tmp_path, Path("/")]
    attempts.clear()

    def fail_chdir(path: Path) -> None:
        attempts.append(path)
        raise OSError

    monkeypatch.setattr(gate_cli.os, "chdir", fail_chdir)
    gate_cli._restore_cwd(None, tmp_path)  # noqa: SLF001, RUF100 - exhausted edge
    assert attempts == [tmp_path, Path("/")]
    emitted: list[object] = []
    base = {"ok": True, "state": "admitted", "target_branch": "dev", "role": "accepted_root", "decision": {"action": "allow"}, "required_gaps": []}  # fmt: skip
    _patch(monkeypatch, hook_cli, resolve_root=lambda _root: tmp_path, emit=lambda result, **_kwargs: emitted.append(result), push_admission_report=lambda **_kwargs: base, campaign_publication_report=lambda _root: {"remote_publication_admission": "allow"})  # fmt: skip
    hook_cli.pre_push("refs/heads/dev", "h", root=tmp_path)
    assert (emitted[-1].ok, emitted[-1].command) == (True, "hook pre-push")
    monkeypatch.setattr(hook_cli, "push_admission_report", lambda **_kwargs: base | {"ok": False})
    hook_cli.pre_push("refs/heads/dev", "h", root=tmp_path)
    assert emitted[-1].ok is False
    _patch(monkeypatch, hook_cli, load_branch_role_policy=lambda _root: BranchRolePolicy(), work_lane_ref_transition_report=lambda **_kwargs: {"ok": True, "state": "admitted", "branch": "work/x", "decision": {"action": "allow"}, "required_gaps": []})  # fmt: skip
    hook_cli.ref_transaction("refs/heads/work/x", "a", "b", root=tmp_path)
    assert (emitted[-1].ok, emitted[-1].command) == (True, "hook ref-transaction")
    for name in ("pre-commit", "pre-push", "reference-transaction"):
        path = tmp_path / ".githooks" / name
        path.parent.mkdir(exist_ok=True)
        path.write_text("x", encoding="utf-8")
    monkeypatch.setattr(hook_cli.git_adapter, "set_hooks_path", lambda *_args: False)
    hook_cli.install(root=tmp_path)
    assert emitted[-1].required_gaps == ("hooks_path_wire_failed",)
    _patch(monkeypatch, hook_cli.git_adapter, set_hooks_path=lambda *_args: True, set_config=lambda *_args: False)  # fmt: skip
    hook_cli.install(root=tmp_path)
    assert set(emitted[-1].required_gaps) == {"hook_config_write_failed:ethos.acceptedBranch", "hook_config_write_failed:gc.packRefs"}  # fmt: skip
