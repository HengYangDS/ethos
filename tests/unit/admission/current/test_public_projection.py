"""Public surfaces preserve current authority before downstream repair actions."""

from __future__ import annotations

import shlex
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.admission.current.authority import resolve_current_authority
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.store.state.lease.lifecycle.effects import revoke_lease
from ethos.adapters.store.state.schema import state_database
from ethos.application.inspection import inspect_repository
from ethos.application.invocation import ACTOR_INPUT
from ethos.contracts.coordination import LeaseOperationRequest
from ethos.contracts.operations.catalog import COMMANDS
from ethos.result import EthosResult
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import init_git_repo
from tests.support.lane_scenarios import leased_worktree

if TYPE_CHECKING:
    from pathlib import Path

_HOLDER = "agent:test:case:agent-a"
_ACTOR_STEP = "rerun the command with --actor <your own identity>"
# What each gap continues to: the step's kind, its operation and the values it leaves to the agent.
_STEPS = {
    "invocation_actor_missing": ("instruction", "", [ACTOR_INPUT.model_dump()]),
    "work_lane_missing_lease": ("decision", "lane.lease.reacquire.preview", []),
    "lease_holder_mismatch": ("decision", "lane.handoff.transfer.preview", []),
}


@pytest.mark.parametrize("policy_declared", [False, True])
@pytest.mark.parametrize(
    ("actor", "gap", "decision_state"),
    [
        (None, "invocation_actor_missing:work/feature", "automatic"),
        ("agent:test:case:agent-a", "work_lane_missing_lease:work/feature", "await-user"),
        ("agent:test:case:other", "lease_holder_mismatch:work/feature", "await-user"),
    ],
)
def test_public_surfaces_preserve_one_current_authority_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    actor: str | None,
    gap: str,
    decision_state: str,
    *,
    policy_declared: bool,
) -> None:
    lane = leased_worktree(init_git_repo(tmp_path / "repo"), tmp_path / "repo-work-feature")
    if policy_declared:
        (lane / ".ethos/workspace.toml").write_text(
            '[commit_policy]\nsubject_pattern = "fix: .+"\n', encoding="utf-8"
        )
    if actor is None:
        monkeypatch.delenv("ETHOS_ACTOR", raising=False)
    else:
        monkeypatch.setenv("ETHOS_ACTOR", actor)
    # The held Lease, read before any command runs, so a handoff names its real coordinates.
    lease = leases_by_branch(lane)["work/feature"]
    if gap.startswith("work_lane_missing_lease:"):
        revoke_lease(
            state_database(lane),
            request=LeaseOperationRequest.model_validate(
                {
                    "operation": "revoke",
                    "branch": "work/feature",
                    "holder_ref": actor,
                    "generation": lease["generation"],
                    "expires_at": lease["expires_at"],
                    "apply": True,
                }
            ),
        )
    path = "README.md"
    editor_root = lane.resolve().as_posix()

    path_arguments = (path, "--editor-root", editor_root, "--require-editor-root", "--json")
    results = tuple(
        runner(*arguments, cwd=lane)
        for runner, arguments in (
            (run_ethos, ("status", "--json")),
            (run_ethos, ("plan", "--changed", "--json")),
            (run_ethos_blocked, ("lane", "prewrite", *path_arguments)),
            (run_ethos_blocked, ("hook", "admit", "pre-tool", *path_arguments)),
            (run_ethos_blocked, ("prove", "--json")),
        )
    )

    assert {result["required_gaps"][0] for result in results} == {gap}
    assert "write_admission_not_armed:runtime_current" in results[0]["required_gaps"]
    handoff = ("lane", "handoff", "transfer", "--generation", str(lease["generation"]))
    handoff += ("--expires-at", str(lease["expires_at"]), "--branch", "work/feature")
    handoff += ("--holder-ref", _HOLDER, "--target-holder-ref", str(actor))
    handoff += ("--root", str(lane), "--json")
    assert {result["next_action"] for result in results} == {
        (f"ethos lane lease reacquire --path {lane} --holder-ref {actor} --root {lane} --json")
        if gap.startswith("work_lane_missing_lease:")
        else shlex.join(("ethos", *handoff))
        if gap.startswith("lease_holder_mismatch:")
        else _ACTOR_STEP
    }
    assert {result["user_decision_required"] for result in results} == {
        decision_state == "await-user"
    }
    steps = [result["next"] for result in results]
    assert [(step["kind"], step["form"], step.get("inputs", [])) for step in steps] == [
        _STEPS[gap.partition(":")[0]]
    ] * len(results)
    # A step that leaves no value to the agent has no `inputs` key, not an empty one.
    assert {"inputs" in step for step in steps} == {bool(_STEPS[gap.partition(":")[0]][2])}
    # The handoff that a mismatch names is live: its preview admits the generation it carries.
    if gap.startswith("lease_holder_mismatch:"):
        assert run_ethos(*handoff, cwd=lane)["verdict"] == "pass"


@pytest.mark.parametrize("missing", [{"generation": 0}, {"expires_at": ""}])
def test_a_foreign_lease_without_its_coordinates_continues_to_lane_status(
    tmp_path: Path, missing: dict[str, object]
) -> None:
    """A handoff that cannot name the generation it moves is no step; the lane's status is."""
    lease: dict[str, object] = {"lease_state": "valid", "holder_ref": _HOLDER, "generation": 1}
    lease |= {"expires_at": "2099-01-01T00:00:00Z"} | missing
    authority = resolve_current_authority(
        root=tmp_path, branch="work/feature", lease=lease, actor="agent:a:b:c", current_head=""
    )

    assert authority.reason == "lease_holder_mismatch:work/feature"
    status = f"ethos lane status --root {tmp_path.resolve().as_posix()} --json"
    assert authority.recovery(tmp_path) == (status, False)


def test_a_foreign_lease_names_the_generation_that_its_read_model_reads(tmp_path: Path) -> None:
    """The handoff carries the generation that the authority's projection reports.

    No producer yields a generation as text; the Lease is built by hand here.
    """
    lease: dict[str, object] = {"lease_state": "valid", "holder_ref": _HOLDER, "generation": "3"}
    lease |= {"expires_at": "2099-01-01T00:00:00Z"}
    authority = resolve_current_authority(
        root=tmp_path, branch="work/feature", lease=lease, actor="agent:a:b:c", current_head=""
    )
    step, decision = authority.recovery(tmp_path)
    generation = authority.projection()["generation"]
    assert (generation, decision) == (3, True)
    assert f"--generation {generation} --expires-at" in step


def test_the_actor_a_step_asks_for_is_supplied_by_its_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--actor` supplies the named input and wins over the fallback; no request declares it."""
    lane = leased_worktree(init_git_repo(tmp_path / "repo"), tmp_path / "repo-work-feature")
    gap = "invocation_actor_missing:work/feature"
    monkeypatch.delenv("ETHOS_ACTOR", raising=False)

    asked = run_ethos("status", "--json", cwd=lane)
    tool = inspect_repository(lane).to_dict()["next"]
    supplied = run_ethos("status", ACTOR_INPUT.flag, _HOLDER, "--json", cwd=lane)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:other")
    preferred = run_ethos("status", ACTOR_INPUT.flag, _HOLDER, "--json", cwd=lane)

    assert (asked["required_gaps"][0], asked["next_action"]) == (gap, _ACTOR_STEP)
    # The operation behind the MCP status tool carries the entry that a tool projection reads.
    entry = {"name": "actor", "flag": "--actor", "description": ACTOR_INPUT.description}
    assert (tool["kind"], tool["inputs"], bool(entry["description"])) == (
        "instruction",
        [entry],
        True,
    )
    # The reader of 0.2.0-beta.11 keeps the inputs of the first step that carries them.
    assert EthosResult.from_payload(asked).to_dict()["next"] == asked["next"]
    assert [gap in result["required_gaps"] for result in (supplied, preferred)] == [False, False]
    assert not [item for item in supplied["required_gaps"] if item.startswith("lease_holder_")]
    assert supplied["required_gaps"] == preferred["required_gaps"]
    # The flag selects no operation, since it is a field of no request.
    assert not [name for name, item in COMMANDS.items() if "actor" in item.request.model_fields]
