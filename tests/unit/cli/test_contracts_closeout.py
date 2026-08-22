from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

import pytest

import ethos.surface.cli.hook.commands as hook_commands
from ethos.adapters.admission.git_admission import push_admission_report
from ethos.adapters.mutation.proof import persist_proof_attestation
from ethos.adapters.mutation.proof import proof_plan
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.adapters.repo.git_effect_attestation import accepted_closeout_attestation
from ethos.contracts.plan import compile_plan
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import Commitment
from ethos.contracts.semantic import Facts
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import issue_conformant_proof
from tests.support.governed_repository import seed_executed_proof
from tests.support.lane_scenarios import add_candidate_worktree
from tests.support.openspec_lifecycle import stub_official_archive_state

if TYPE_CHECKING:
    from pathlib import Path


def _closeout_repo(tmp_path: Path, *, changed: bool = False) -> tuple[Path, Path, str, str]:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    accepted_head = git(repo, "rev-parse", "HEAD")
    if changed:
        commit_fixture_file(candidate, "README.md", "# candidate change\n", "candidate change")
    return repo, candidate, accepted_head, git(candidate, "rev-parse", "HEAD")


def _closeout(
    repo: Path,
    *args: str,
    expect_head: str | None = None,
    blocked: bool = False,
) -> dict[str, object]:
    command = ["land", "--closeout", *args]
    if expect_head is not None:
        command.extend(("--expect-head", expect_head))
    command.append("--json")
    runner = run_ethos_blocked if blocked else run_ethos
    return runner(*command, cwd=repo)


def _add_archived_proof(candidate: Path, head: str) -> None:
    base = proof_plan(candidate, head=head, changed_paths=("README.md",))
    proof = issue_conformant_proof(candidate, head, plan=base, issued_at=datetime.now(UTC))
    values = dict(base.facts["values"])
    effect_identity = "d" * 64
    plan = compile_plan(
        Commitment.model_validate(dict(base.commitment)).model_copy(
            update={"id": "change:historical-closeout"}
        ),
        Facts.model_validate(
            base.facts
            | {
                "observed_at": datetime.now(UTC),
                "values": values | {"change_id": "historical-closeout"},
            }
        ),
        base.nodes,
        policy=dict(base.policy),
        prior_attestations={
            "openspec_archive": {
                "predicate": "effect:openspec-archive",
                "attestation_id": "a" * 64,
                "commitment_digest": "b" * 64,
                "effect_digest": "c" * 64,
                "effect_identity": effect_identity,
                "input": {"effect_identity": effect_identity},
                "output": {"changed_paths": ["README.md"]},
                "authorized_paths": ["README.md"],
            }
        },
    )
    payload = proof.model_dump(mode="python", exclude={"id"}) | {
        "commitment_digest": plan.inputs.commitment,
        "facts_digest": plan.inputs.facts,
        "plan_digest": plan.digest,
        "policy_digest": plan.inputs.policy,
        "effect_digest": plan.inputs.effect,
        "payload": {
            "kind": proof.payload.kind,
            "body": proof.payload.body | {"plan": plan.model_dump(mode="json")},
        },
    }
    persist_proof_attestation(candidate, Attestation.issue(payload))


def test_land_closeout_apply_fast_forwards_accepted_root_from_candidate(tmp_path: Path) -> None:
    repo, candidate, accepted_head, candidate_head = _closeout_repo(tmp_path, changed=True)
    _add_archived_proof(candidate, candidate_head)
    payload = _closeout(repo, "--apply", "--authorize", expect_head=accepted_head)
    assert payload["state"] == "accepted_validated"
    resolution = payload["data"]["closeout_resolution"]
    coordinates = resolution["coordinates"]
    assert tuple(
        coordinates[key] for key in ("accepted_head", "candidate_head", "candidate_tree")
    ) == (accepted_head, candidate_head, git(candidate, "rev-parse", f"{candidate_head}^{{tree}}"))
    attestation = payload["data"]["accepted_update"]["attestation"]
    assert resolution["proof"]["plane"] == "local"
    assert resolution["proof"]["external_receipt"] == {}
    assert resolution["proof"]["repository_attestation_id"] == resolution["proof"]["attestation_id"]
    assert resolution["effect"]["attestation_id"] == attestation["id"]
    assert git(repo, "rev-parse", "dev") == candidate_head
    git(repo, "update-ref", "refs/heads/dev", accepted_head, candidate_head)
    push = push_admission_report(
        root=repo,
        target_ref="refs/heads/dev",
        pushed_head=candidate_head,
        remote_head=accepted_head,
    )
    assert (push["verdict"], push["accepted_closeout_effect"]["attestation_id"]) == (
        "pass",
        attestation["id"],
    )
    record_attestations(
        repo,
        (
            Attestation.issue(
                Attestation.model_validate(attestation).model_dump(mode="python", exclude={"id"})
                | {"verifier": "agent:test:case:other-closeout"}
            ),
        ),
    )

    with pytest.raises(ValueError, match="accepted_closeout_effect_ambiguous"):
        accepted_closeout_attestation(
            repo,
            accepted_ref="refs/heads/dev",
            candidate_ref="refs/heads/candidate/dev",
            candidate_head=candidate_head,
        )


def test_status_plan_closeout_and_hook_share_exact_apply_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, candidate, accepted_head, candidate_head = _closeout_repo(tmp_path, changed=True)
    _add_archived_proof(candidate, candidate_head)

    closeout = _closeout(repo)
    status = run_ethos("status", "--json", cwd=repo)
    plan = run_ethos("plan", "--json", cwd=repo)
    emitted: list[object] = []
    monkeypatch.setattr(hook_commands, "resolve_root", lambda _root: candidate)
    monkeypatch.setattr(hook_commands, "emit", lambda result, **_kwargs: emitted.append(result))
    hook_commands.pre_push(
        "refs/heads/dev",
        candidate_head,
        options=hook_commands.PushOptions(remote_head=accepted_head, json_output=True),
    )
    expected = closeout["next_action"]
    assert {
        closeout["next_action"],
        status["next_action"],
        plan["next_action"],
        emitted[-1].next_action,
    } == {expected}
    monkeypatch.setattr(
        "ethos.surface.cli.root.planning.openspec_governance_report",
        lambda *_args, **_kwargs: {
            "verdict": "block",
            "required_gaps": ["model_gap"],
            "intent_context": {},
        },
    )

    gapped = run_ethos("plan", "--json", cwd=repo)
    assert (gapped["verdict"], gapped["required_gaps"], gapped["next_action"]) == (
        "block",
        ["model_gap"],
        expected,
    )


def test_land_closeout_rejects_stale_candidate_coordinate(tmp_path: Path) -> None:
    repo, candidate, accepted_head, candidate_head = _closeout_repo(tmp_path, changed=True)
    _add_archived_proof(candidate, candidate_head)
    expected = _closeout(repo)["next_action"]
    payload = _closeout(
        repo,
        "--apply",
        "--authorize",
        "--candidate-head",
        "0" * 40,
        expect_head=accepted_head,
        blocked=True,
    )

    assert (payload["verdict"], payload["required_gaps"], payload["data"]["accepted_update"]) == (
        "block",
        ["candidate_head_expectation_mismatch"],
        {},
    )
    assert payload["next_action"] == expected
    assert git(repo, "rev-parse", "dev") == accepted_head


def test_land_closeout_defers_control_replacement_without_signed_receipt(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    candidate = tmp_path / "repo-candidate-dev"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
    profile = candidate / ".ethos" / "profile.toml"
    profile.write_text(
        profile.read_text(encoding="utf-8") + '\n[independent_verification]\nmode = "required"\n',
        encoding="utf-8",
    )
    path = candidate / "src" / "ethos" / "adapters" / "admission"
    path.mkdir(parents=True, exist_ok=True)
    (path / "new_control.py").write_text("CONTROL = 'candidate'\n", encoding="utf-8")
    git(candidate, "add", ".")
    git(
        candidate,
        "commit",
        "-m",
        "replace admission control",
    )
    candidate_head = git(candidate, "rev-parse", "HEAD")
    seed_executed_proof(candidate, candidate_head)
    payload = run_ethos_blocked(
        "land",
        "--closeout",
        "--apply",
        "--authorize",
        "--expect-head",
        git(repo, "rev-parse", "HEAD"),
        "--json",
        cwd=repo,
    )
    control = payload["data"]["control_replacement"]
    assert (control["required"], control["verdict"], payload["state"]) == (
        True,
        "unknown",
        "deferred",
    )
    bootstrap = payload["data"]["closeout_bootstrap"]
    verification = bootstrap["independent_verification"]
    assert tuple(
        verification[key]
        for key in ("required", "proof_floor_id", "trust_boundary", "mints_authority")
    ) == (True, "ethos:control-replacement:v1", "protected-provider", False)
    assert "<" not in payload["next_action"]
    assert payload["next_action"].startswith("ethos land --closeout")
    assert f"--expect-head {git(repo, 'rev-parse', 'HEAD')}" in payload["next_action"]
    assert f"--candidate-head {candidate_head}" in payload["next_action"]
    assert f"--root {repo.resolve().as_posix()}" in payload["next_action"]
    assert git(repo, "rev-parse", "HEAD") != candidate_head


def test_land_closeout_audits_candidate_content_before_fast_forward(
    tmp_path: Path, monkeypatch
) -> None:
    repo, candidate, accepted_head, candidate_head = _closeout_repo(tmp_path, changed=True)
    seed_executed_proof(candidate, candidate_head)

    def fake_audit(root: Path, *, openspec_mode: str = "shape") -> dict[str, object]:
        assert openspec_mode == "shape"
        if root.resolve() == candidate.resolve():
            return {"verdict": "pass", "required_gaps": [], "root": root.as_posix()}
        return {
            "verdict": "block",
            "required_gaps": ["accepted_root_precloseout_audit"],
            "root": root.as_posix(),
        }

    monkeypatch.setattr("ethos.domain.status.audit_for_root", fake_audit)
    payload = _closeout(repo, "--apply", "--authorize", expect_head=accepted_head)
    assert payload["verdict"] == "pass"
    assert payload["required_gaps"] == []
    assert payload["data"]["repository_audit"]["root"] == candidate.as_posix()


def test_land_closeout_apply_is_noop_when_candidate_matches_accepted_without_proof(
    tmp_path: Path,
) -> None:
    repo, _candidate, accepted_head, _candidate_head = _closeout_repo(tmp_path)
    payload = _closeout(repo, "--apply", "--authorize", expect_head=accepted_head)
    assert payload["verdict"] == "pass"
    assert payload["state"] == "accepted_current"
    assert payload["required_gaps"] == []
    assert payload["next_action"] == "ethos publish"
    accepted_update = payload["data"]["accepted_update"]
    assert accepted_update["state"] == "accepted_current"
    assert accepted_update["head"] == accepted_head
    assert accepted_update["previous_head"] == accepted_head
    assert accepted_update["attestation"] == {}
    assert git(repo, "rev-parse", "HEAD") == accepted_head


def test_land_closeout_blocks_candidate_with_completed_active_openspec_change(
    tmp_path: Path, monkeypatch
) -> None:
    repo, candidate, _accepted_head, _candidate_head = _closeout_repo(tmp_path, changed=True)
    seed_executed_proof(candidate, _candidate_head)

    def fake_audit(root: Path, *, openspec_mode: str = "shape") -> dict[str, object]:
        assert root.resolve() == candidate.resolve()
        assert openspec_mode == "shape"
        return {"verdict": "pass", "required_gaps": [], "root": root.as_posix()}

    monkeypatch.setattr("ethos.domain.status.audit_for_root", fake_audit)
    stub_official_archive_state(monkeypatch, completed=True, change_name="sample-change")
    payload = _closeout(repo)
    assert payload["verdict"] == "block"
    assert payload["state"] == "blocked"
    assert "openspec_completed_change_unarchived:sample-change" in payload["required_gaps"]
    assert payload["data"]["openspec_lifecycle"]["root"] == candidate.as_posix()
