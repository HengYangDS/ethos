from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.mutation.lane_lifecycle.lease import execute_lease_operation
from ethos.adapters.mutation.lanes import start_work_lane
from ethos.adapters.store.state.lease.lifecycle.core import acquire_lease
from ethos.adapters.store.state.lease.projection import active_leases
from ethos_core.contracts.lifecycle.core import LeaseOperationRequest
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.lane_helpers import add_candidate_worktree
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo

if TYPE_CHECKING:
    from pathlib import Path


HOLDER_A = "agent:test:case:holder-a"
HOLDER_B = "agent:test:case:holder-b"


def _started_lane(tmp_path: Path) -> tuple[Path, Path, dict[str, object]]:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    report = start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        holder_ref=HOLDER_A,
        apply=True,
    )
    assert report["ok"] is True
    return repo, worktree, report


def _lease_args(report: dict[str, object], worktree: Path) -> tuple[str, ...]:
    lease = report["lease"]
    assert isinstance(lease, dict)
    return (
        "--branch",
        "work/feature",
        "--holder-ref",
        HOLDER_A,
        "--lease-id",
        str(lease["lease_id"]),
        "--epoch",
        str(lease["epoch"]),
        "--expect-head",
        git(worktree, "rev-parse", "HEAD"),
    )


def test_unknown_lease_operation_blocks_with_mutation_envelope(tmp_path: Path) -> None:
    _, worktree, started = _started_lane(tmp_path)
    lease = started["lease"]
    assert isinstance(lease, dict)

    report = execute_lease_operation(
        root=worktree,
        request=LeaseOperationRequest(
            operation="unknown",
            branch="work/feature",
            holder_ref=HOLDER_A,
            lease_id=str(lease["lease_id"]),
            expected_epoch=int(lease["epoch"]),
            expect_head=git(worktree, "rev-parse", "HEAD"),
        ),
    )

    assert report["required_gaps"] == ["lease_transition_unknown:unknown"]
    assert report["mutation"]["decision"]["verdict"] == "block"


def test_lane_lease_renew_is_generation_bound_and_emits_receipt(tmp_path: Path) -> None:
    _, worktree, started = _started_lane(tmp_path)

    payload = run_ethos(
        "lane",
        "lease",
        "renew",
        *_lease_args(started, worktree),
        "--ttl-seconds",
        "120",
        "--apply",
        "--root",
        worktree.as_posix(),
        "--json",
        cwd=worktree,
    )

    assert payload["ok"] is True
    assert payload["state"] == "renewed"
    assert payload["data"]["lease"]["holder_ref"] == HOLDER_A
    assert payload["data"]["lease"]["epoch"] == 1
    assert payload["data"]["mutation"]["decision"]["subject"]["action"] == "lane.lease.renew"
    assert payload["data"]["receipt"]["operation"] == "renew"
    assert payload["data"]["receipt"]["applied"] is True
    assert payload["data"]["receipt"]["mints_authority"] is False


def test_lane_lease_renew_blocks_stale_epoch_before_effect(tmp_path: Path) -> None:
    _, worktree, started = _started_lane(tmp_path)
    args = list(_lease_args(started, worktree))
    args[args.index("--epoch") + 1] = "2"

    payload = run_ethos_blocked(
        "lane",
        "lease",
        "renew",
        *args,
        "--apply",
        "--root",
        worktree.as_posix(),
        "--json",
        cwd=worktree,
    )

    assert payload["ok"] is False
    assert "lease_epoch_stale:2!=1" in payload["required_gaps"]
    assert payload["data"]["receipt"] == {}


def test_lane_lease_resume_only_revives_expired_same_generation(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    worktree = tmp_path / "repo-work-feature"
    git(repo, "worktree", "add", "-b", "work/feature", worktree.as_posix(), "dev")
    lease = acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject="work/feature",
        holder_ref=HOLDER_A,
        ttl_seconds=-1,
        payload={
            "path": worktree.as_posix(),
            "expected_head": git(worktree, "rev-parse", "HEAD"),
        },
    )

    payload = run_ethos(
        "lane",
        "lease",
        "resume",
        "--branch",
        "work/feature",
        "--holder-ref",
        HOLDER_A,
        "--lease-id",
        str(lease["lease_id"]),
        "--epoch",
        str(lease["epoch"]),
        "--expect-head",
        git(worktree, "rev-parse", "HEAD"),
        "--apply",
        "--root",
        worktree.as_posix(),
        "--json",
        cwd=worktree,
    )

    assert payload["ok"] is True
    assert payload["state"] == "resumed"
    assert payload["data"]["lease"]["lease_id"] == lease["lease_id"]
    assert payload["data"]["lease"]["epoch"] == lease["epoch"]


def test_lane_handoff_requires_offer_target_and_quiescence_confirmation(
    tmp_path: Path,
) -> None:
    repo, worktree, started = _started_lane(tmp_path)
    common_args = _lease_args(started, worktree)

    offered = run_ethos(
        "lane",
        "handoff",
        "offer",
        *common_args,
        "--target-holder-ref",
        HOLDER_B,
        "--apply",
        "--root",
        worktree.as_posix(),
        "--json",
        cwd=worktree,
    )
    offer_id = offered["data"]["handoff_offer"]["offer_id"]

    blocked = run_ethos_blocked(
        "lane",
        "handoff",
        "accept",
        "--branch",
        "work/feature",
        "--target-holder-ref",
        HOLDER_B,
        "--offer-id",
        offer_id,
        "--lease-id",
        str(started["lease"]["lease_id"]),
        "--epoch",
        "1",
        "--expect-head",
        git(worktree, "rev-parse", "HEAD"),
        "--apply",
        "--root",
        worktree.as_posix(),
        "--json",
        cwd=worktree,
    )
    assert "holder_quiescence_confirmation_required" in blocked["required_gaps"]

    accepted = run_ethos(
        "lane",
        "handoff",
        "accept",
        "--branch",
        "work/feature",
        "--target-holder-ref",
        HOLDER_B,
        "--offer-id",
        offer_id,
        "--lease-id",
        str(started["lease"]["lease_id"]),
        "--epoch",
        "1",
        "--expect-head",
        git(worktree, "rev-parse", "HEAD"),
        "--confirm-holder-quiesced",
        "--apply",
        "--root",
        worktree.as_posix(),
        "--json",
        cwd=worktree,
    )

    assert accepted["state"] == "handoff_accepted"
    assert accepted["data"]["lease"]["holder_ref"] == HOLDER_B
    assert accepted["data"]["lease"]["epoch"] == 2
    assert accepted["data"]["mutation"]["request"]["confirmation_present"] is True
    leases = active_leases(repo / ".ethos" / "state" / "state.sqlite")
    assert [(row["holder_ref"], row["epoch"]) for row in leases] == [(HOLDER_B, 2)]
