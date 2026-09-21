"""Public accepted closeout preserves exact proof, intent and Git coordinates."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

import pytest
import tomli_w

import ethos.adapters.admission.evidence.external as evidence
import ethos.adapters.repo.status.workspace as workspace
import ethos.domain.land.closeout as closeout
import ethos.domain.land.operation as land_commands
import ethos.surface.cli.hook.commands as hook_commands
from ethos.adapters.admission.publication import push_admission_report
from ethos.adapters.mutation.proof import proof_for_repository_transition
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.adapters.repo.git_effect_attestation import accepted_closeout_attestation
from ethos.adapters.repo.git_effect_attestation import plan_from_attestation
from ethos.adapters.repo.worktree_effects import sync_worktree
from ethos.contracts.semantic import Attestation
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import prepared_work_lane
from tests.support.lane_scenarios import add_candidate_worktree
from tests.support.proof import seed_executed_proof

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path
    from typing import Any

    from ethos.result import EthosResult


def _land_candidate(repo: Path, head: str) -> None:
    """Seed the exact fixture proof and exercise native candidate integration."""
    seed_executed_proof(repo, head)
    run_ethos("land", "--apply", "--authorize", "--expect-head", head, "--json", cwd=repo)


def _archive_change(repo: Path, head: str, *, blocked: bool = False) -> dict[str, Any]:
    """Exercise the same official archive transport for allowed and rejected fixture changes."""
    runner = run_ethos_blocked if blocked else run_ethos
    return runner(
        "lane",
        "archive-change",
        "--change",
        "fixture-change",
        "--expect-head",
        head,
        "--apply",
        "--json",
        cwd=repo,
    )


def _closeout_repo(
    tmp_path: Path, *, changed: bool = False, mirror: str = "independent"
) -> tuple[Path, Path, str, str]:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo, release_mirror=mirror)
    if mirror == "accepted_ff":
        git(repo, "branch", "main")
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
) -> dict[str, Any]:
    command = ["land", "--closeout", *args]
    if expect_head is not None:
        command.extend(("--expect-head", expect_head))
    command.append("--json")
    runner = run_ethos_blocked if blocked else run_ethos
    return runner(*command, cwd=repo)


def _archived_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    prepare: Callable[[Path], None] | None = None,
) -> tuple[Path, Path, str, str]:
    fixture = prepared_work_lane(tmp_path)
    accepted_head = git(fixture.repository, "rev-parse", "HEAD")
    commit_fixture_file(fixture.worktree, "README.md", "# candidate change\n", "candidate change")
    if prepare is not None:
        prepare(fixture.worktree)
        commit_fixture(fixture.worktree, "prepare candidate change")
    head = commit_fixture_file(
        fixture.worktree,
        "openspec/changes/fixture-change/tasks.md",
        "- [x] Exercise fixture lifecycle\n",
        "complete fixture change",
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    seed_executed_proof(fixture.worktree, head)
    _archive_change(fixture.worktree, head)
    archived_head = git(fixture.worktree, "rev-parse", "HEAD")
    _land_candidate(fixture.worktree, archived_head)
    return fixture.repository, fixture.candidate, accepted_head, archived_head


def test_source_acceptance_preserves_pending_delivery_until_official_archive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One Change survives real Git integration, later delivery and archive."""
    fixture = prepared_work_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    tasks = "openspec/changes/fixture-change/tasks.md"
    pending = "- [ ] Observe delivered source after accepted integration\n"
    head = commit_fixture_file(fixture.worktree, tasks, pending, "declare delivery obligation")
    accepted = git(fixture.repository, "rev-parse", "HEAD")
    seed_executed_proof(fixture.worktree, head)

    archive = _archive_change(fixture.worktree, head, blocked=True)
    assert "openspec_change_incomplete:fixture-change" in archive["required_gaps"]
    assert git(fixture.worktree, "rev-parse", "HEAD") == head
    assert (fixture.worktree / tasks).read_text() == pending

    run_ethos(
        "land",
        "--apply",
        "--authorize",
        "--expect-head",
        head,
        "--json",
        cwd=fixture.worktree,
    )
    result = _closeout(fixture.repository, "--apply", "--authorize", expect_head=accepted)
    assert result["verdict"] == "pass"
    assert git(fixture.repository, "rev-parse", "HEAD") == head
    assert (fixture.repository / tasks).read_text() == pending
    assert (fixture.candidate / tasks).read_text() == pending
    assert (fixture.worktree / tasks).read_text() == pending

    delivered = commit_fixture_file(
        fixture.worktree, tasks, pending.replace("[ ]", "[x]"), "record observed delivery"
    )
    seed_executed_proof(fixture.worktree, delivered)
    _archive_change(fixture.worktree, delivered)
    archived = git(fixture.worktree, "rev-parse", "HEAD")
    assert not (fixture.worktree / tasks).exists()
    _land_candidate(fixture.worktree, archived)
    assert (
        _closeout(fixture.repository, "--apply", "--authorize", expect_head=head)["verdict"]
        == "pass"
    )
    assert git(fixture.repository, "rev-parse", "HEAD") == archived
    assert not (fixture.repository / tasks).exists()


@pytest.mark.parametrize("replace_gate", [False, True])
def test_land_closeout_apply_fast_forwards_accepted_root_from_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, replace_gate: bool
) -> None:
    def prepare(worktree: Path) -> None:
        profile = worktree / ".ethos/profile.toml"
        declaration = tomllib.loads(profile.read_text())
        declaration["proof"]["gates"][0]["command"] = ["python", "-c", "print('replacement')"]
        profile.write_text(tomli_w.dumps(declaration))

    repo, candidate, accepted_head, candidate_head = _archived_candidate(
        tmp_path, monkeypatch, prepare=prepare if replace_gate else None
    )
    if replace_gate:
        preview = land_commands.land_repository(
            repo, closeout=True, expect_head=accepted_head
        ).to_dict()
        assert preview == _closeout(repo, expect_head=accepted_head)
        assert preview["verdict"] == "pass"
        rejected = _closeout(
            repo, "--apply", "--authorize", expect_head=accepted_head, blocked=True
        )
        assert rejected["required_gaps"] == ["control_replacement_candidate_head_required"]
        assert git(repo, "rev-parse", "dev") == accepted_head
    payload = land_commands.land_repository(
        repo,
        closeout=True,
        apply=True,
        authorize=True,
        candidate_head=candidate_head,
        expect_head=accepted_head,
    ).to_dict()
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
    effect = push["accepted_closeout_effect"]
    assert isinstance(effect, dict)
    assert (push["verdict"], effect["attestation_id"]) == (
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


def test_closeout_selects_archived_candidate_proof_not_worktree_projection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, candidate, accepted_head, candidate_head = _archived_candidate(tmp_path, monkeypatch)
    proof, gaps = proof_for_repository_transition(candidate, candidate_head)
    assert gaps == []
    assert proof is not None
    projection = sync_worktree(
        repo,
        candidate,
        branch="candidate/dev",
        previous=candidate_head,
        head=candidate_head,
    )
    assert projection.predicate == "effect:git-worktree-index"
    assert projection.commitment_digest is None
    record_attestations(repo, (projection,))

    payload = _closeout(repo, "--apply", "--authorize", expect_head=accepted_head)

    resolution = payload["data"]["closeout_resolution"]
    assert resolution["proof"]["repository_attestation_id"] == proof.id
    accepted_effect = Attestation.model_validate(payload["data"]["accepted_update"]["attestation"])
    accepted_plan = plan_from_attestation(accepted_effect)
    assert accepted_plan.prior_attestations["proof"]["id"] == proof.id
    assert accepted_plan.prior_attestations["proof"]["commitment_digest"] == (
        proof.commitment_digest
    )


def test_status_plan_closeout_and_hook_share_exact_apply_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, candidate, accepted_head, candidate_head = _archived_candidate(tmp_path, monkeypatch)

    closeout = _closeout(repo)
    status = run_ethos("status", "--json", cwd=repo)
    plan = run_ethos("plan", "--json", cwd=repo)
    emitted: list[EthosResult] = []
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
        "ethos.adapters.admission.current.resolution.openspec_governance_report",
        lambda *_args, **_kwargs: {
            "verdict": "block",
            "required_gaps": ["model_gap"],
            "intent_context": {},
        },
    )

    gapped = run_ethos("plan", "--json", cwd=repo)
    assert (gapped["verdict"], gapped["required_gaps"], gapped["next_action"]) == (
        "pass",
        [],
        expected,
    )


def test_land_closeout_rejects_stale_candidate_coordinate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _candidate, accepted_head, _candidate_head = _archived_candidate(tmp_path, monkeypatch)
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


def test_land_closeout_defers_control_replacement_without_signed_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = tmp_path / "missing-provider.toml"
    monkeypatch.setattr(evidence, "_SYSTEM_PROVIDER_CONFIGS", (config,))

    def prepare(worktree: Path) -> None:
        profile = worktree / ".ethos" / "profile.toml"
        profile.write_text(
            profile.read_text(encoding="utf-8")
            + '\n[independent_verification]\nmode = "required"\n',
            encoding="utf-8",
        )
        path = worktree / "src" / "ethos" / "adapters" / "admission"
        path.mkdir(parents=True, exist_ok=True)
        (path / "new_control.py").write_text("CONTROL = 'candidate'\n", encoding="utf-8")

    repo, candidate, _accepted_head, candidate_head = _archived_candidate(
        tmp_path, monkeypatch, prepare=prepare
    )
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
        "block",
        "blocked",
    )
    bootstrap = payload["data"]["closeout_bootstrap"]
    verification = bootstrap["independent_verification"]
    assert tuple(
        verification[key]
        for key in ("required", "proof_floor_id", "trust_boundary", "mints_authority")
    ) == (True, "ethos:control-replacement:v1", "protected-provider", False)
    assert payload["required_gaps"] == ["independent_verification_provider_config_missing"]
    assert str(config) in payload["next_action"]
    assert not payload["next_action"].startswith("ethos land")
    assert verification["receipt_option"] == ""
    assert payload["next_action"] == control["independent_verification"]["next_action"]
    assert git(repo, "rev-parse", "HEAD") != candidate_head

    for selection in ((), ("--ref", "refs/heads/dev")):
        runner = run_ethos_blocked if selection else run_ethos
        observed = runner("publish", *selection, "--json", cwd=candidate)
        assert "independent_verification_provider_config_missing" in observed["required_gaps"]
        assert observed["next_action"] == payload["next_action"]


def test_land_closeout_audits_candidate_content_before_fast_forward(
    tmp_path: Path, monkeypatch
) -> None:
    repo, candidate, accepted_head, _candidate_head = _archived_candidate(tmp_path, monkeypatch)

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


@pytest.mark.parametrize("mirror", ["independent", "accepted_ff"])
@pytest.mark.parametrize("proven", [False, True])
def test_current_closeout_preserves_proven_or_unattested_state(
    tmp_path: Path,
    mirror: str,
    *,
    proven: bool,
) -> None:
    """Fresh preview and apply observe the original effect, not a new no-op transaction."""
    repo, candidate, accepted, head = _closeout_repo(tmp_path, changed=proven, mirror=mirror)
    effect = {}
    if proven:
        seed_executed_proof(candidate, head)
        first = _closeout(repo, "--apply", "--authorize", expect_head=accepted)
        effect = first["data"]["accepted_update"]["attestation"]
    refs = git(repo, "show-ref")
    for args in ((), ("--apply", "--authorize")):
        result = _closeout(repo, *args, expect_head=head)
        assert (result["verdict"], result["state"]) == ("pass", "accepted_current")
        assert result["required_gaps"] == []
        update = result["data"]["accepted_update"]
        assert (update["state"], update["head"], update["previous_head"]) == (
            "accepted_current",
            head,
            head,
        )
        assert update["attestation"] == effect
        assert result["data"]["closeout_resolution"]["effect"]["attestation_id"] == effect.get(
            "id", ""
        )
        assert result["next_action"] == "ethos publish"
        assert git(repo, "show-ref") == refs
        assert git(repo, "rev-parse", "HEAD") == head


def test_land_closeout_observes_completed_active_openspec_change(
    tmp_path: Path, monkeypatch
) -> None:
    """Completed native intent stays valid until its deliberate archive effect."""
    fixture = prepared_work_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    head = commit_fixture_file(
        fixture.worktree,
        "openspec/changes/fixture-change/tasks.md",
        "- [x] Exercise fixture lifecycle\n",
        "complete source work",
    )
    _land_candidate(fixture.worktree, head)

    payload = _closeout(fixture.repository)
    assert payload["verdict"] == "pass", payload
    assert payload["required_gaps"] == []
    assert payload["data"]["openspec_lifecycle"]["completed_changes"] == ["fixture-change"]
    assert payload["data"]["openspec_lifecycle"]["root"] == fixture.candidate.as_posix()


@pytest.mark.parametrize("projection", ["command", "bootstrap", "candidate"])
def test_closeout_projection_does_not_collect_unrelated_workspace_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, projection: str
) -> None:
    """Ref and topology projections do not rerun runtime and Lease admission."""
    repo, candidate, accepted, proposed = _closeout_repo(tmp_path)

    def reject_full_observation(*_args, **_kwargs):
        pytest.fail("projection unnecessarily collected complete workspace authority")

    if projection == "candidate":
        monkeypatch.setattr(land_commands, "workspace_status", reject_full_observation)
        monkeypatch.setattr(workspace, "workspace_status_observation", reject_full_observation)
        initial = _closeout(repo)
        assert initial["data"]["closeout_resolution"]["coordinates"]["candidate_head"] == proposed
        later = commit_fixture_file(candidate, "later.txt", "later\n", "advance candidate")
        changed = _closeout(repo)
        assert changed["data"]["closeout_resolution"]["coordinates"]["candidate_head"] == later
        assert git(repo, "rev-parse", "HEAD") == accepted
        (candidate / "untracked.txt").touch()
        assert "candidate_worktree_dirty" in _closeout(repo)["required_gaps"]
        return
    monkeypatch.setattr(workspace, "workspace_status_observation", reject_full_observation)
    if projection == "command":
        command = closeout.closeout_apply_command(
            candidate, accepted_head=accepted, candidate_head=proposed
        )
        assert f"--root {repo.resolve().as_posix()} --json" in command
        assert f"--candidate-head {proposed}" in command
    else:
        result = closeout.closeout_bootstrap_package(
            repo=candidate,
            audit_root=candidate,
            required_gaps=(),
            accepted_head=accepted,
            candidate_head=proposed,
        )
        assert result["accepted_root"] == repo.resolve().as_posix()
        proof_target = result["proof_target"]
        assert isinstance(proof_target, dict)
        assert proof_target["root"] == candidate.resolve().as_posix()
        assert result["candidate_head"] == proposed
