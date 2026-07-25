from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import pytest

import ethos.adapters.mutation.resolution.closeout.recovery as recovery_adapter
from ethos.adapters.mutation.resolution.lane import apply_lane_resolution
from ethos.adapters.mutation.resolution.lane import plan_lane_resolution
from ethos.adapters.mutation.resolution.observation import observe_lane
from ethos.adapters.mutation.resolution.records.clear.core import LaneResolutionClearRequest
from ethos.adapters.mutation.resolution.records.clear.core import clear_lane_resolution_package
from ethos.adapters.mutation.resolution.records.inventory import lane_resolution_inventory
from ethos.adapters.mutation.resolution.records.roots import accepted_control_root
from ethos.surface.cli.lane.resolution import _default_decision_path
from ethos_core.contracts.resolution.lane import LaneObservation
from tests.support.contract_helpers import commit_fixture_file
from tests.support.lane_helpers import git
from tests.support.lane_helpers import orphan_work_lane


@dataclass(frozen=True)
class _ChronicleBinding:
    target_branch: str | None = None
    target_branch_sha256: str | None = None
    target_head: str | None = None
    event: str = "lane_resolution/preserve-retire"
    revision: str = "one"


def _bound_chronicle(
    root: Path,
    *,
    branch: str,
    relative: str = "evidence/chronicle/target-binding/preserve-retire.md",
    binding: _ChronicleBinding | None = None,
) -> str:
    binding = _ChronicleBinding() if binding is None else binding
    control_root = accepted_control_root(root)
    observation, gaps = observe_lane(control_root, branch)
    assert gaps == []
    fields = [f"event: {binding.event}"]
    if binding.target_branch is not None:
        fields.append(f"target_branch: {binding.target_branch}")
    if binding.target_branch_sha256 is not None:
        fields.append(f"target_branch_sha256: {binding.target_branch_sha256}")
    if binding.target_branch is None and binding.target_branch_sha256 is None:
        fields.append(f"target_branch: {observation.lane_ref}")
    fields.append(f"target_head: {binding.target_head or observation.head}")
    content = "---\n" + "\n".join(fields) + f"\n---\n\nrevision: {binding.revision}\n"
    commit_fixture_file(
        control_root,
        relative,
        content,
        f"record target-bound chronicle {binding.revision}",
    )
    return relative


def _plan(root: Path, *, chronicle_ref: str) -> dict[str, object]:
    return plan_lane_resolution(
        root=root,
        branch="work/orphan",
        disposition="preserve-retire",
        reason="Preserve one exact diverged predecessor before retirement.",
        evidence_refs=("evidence:maintainer-decision",),
        chronicle_ref=chronicle_ref,
        recovery_plan="Preserve the observed target before any destructive effect.",
        decision_path=_default_decision_path(root, "work/orphan"),
        break_glass=True,
        apply=True,
    )


def test_preserve_retire_rejects_unbound_accepted_chronicle(tmp_path: Path) -> None:
    repo, _lane = orphan_work_lane(tmp_path)
    chronicle_ref = "evidence/chronicle/target-binding/unbound.md"
    commit_fixture_file(
        repo,
        chronicle_ref,
        "decision: lane_resolution/preserve-retire\n",
        "record unbound preserve-retire decision",
    )

    planned = _plan(repo, chronicle_ref=chronicle_ref)

    assert planned["ok"] is False
    assert planned["required_gaps"] == ["lane_resolution_chronicle_invalid"]


@pytest.mark.parametrize(
    ("target_branch", "target_head", "event", "expected_gap"),
    [
        (
            "work/other",
            None,
            "lane_resolution/preserve-retire",
            "lane_resolution_chronicle_invalid",
        ),
        (None, "0" * 40, "lane_resolution/preserve-retire", "lane_resolution_chronicle_invalid"),
        (None, None, "lane_resolution/retire", "lane_resolution_chronicle_disposition_mismatch"),
    ],
    ids=("branch-mismatch", "head-mismatch", "event-mismatch"),
)
def test_preserve_retire_rejects_nonmatching_target_binding(
    tmp_path: Path,
    target_branch: str | None,
    target_head: str | None,
    event: str,
    expected_gap: str,
) -> None:
    repo, _lane = orphan_work_lane(tmp_path)
    chronicle_ref = _bound_chronicle(
        repo,
        branch="work/orphan",
        binding=_ChronicleBinding(
            target_branch=target_branch,
            target_head=target_head,
            event=event,
        ),
    )

    planned = _plan(repo, chronicle_ref=chronicle_ref)

    assert planned["ok"] is False
    assert planned["required_gaps"] == [expected_gap]


def test_preserve_retire_accepts_hashed_target_branch_selector(tmp_path: Path) -> None:
    repo, _lane = orphan_work_lane(tmp_path)
    target_branch_sha256 = hashlib.sha256(b"work/orphan").hexdigest()
    chronicle_ref = _bound_chronicle(
        repo,
        branch="work/orphan",
        binding=_ChronicleBinding(target_branch_sha256=target_branch_sha256),
    )

    planned = _plan(repo, chronicle_ref=chronicle_ref)

    assert planned["ok"] is True


def test_preserve_retire_uses_the_configured_accepted_chronicle_root(tmp_path: Path) -> None:
    repo, _lane = orphan_work_lane(tmp_path)
    carrier = tmp_path / "repo-work-carrier"
    git(repo, "worktree", "add", "-b", "work/carrier", carrier.as_posix(), "dev")
    chronicle_ref = "evidence/chronicle/target-binding/carrier-only.md"
    observation, gaps = observe_lane(carrier, "work/orphan")
    assert gaps == []
    commit_fixture_file(
        carrier,
        chronicle_ref,
        "---\n"
        "event: lane_resolution/preserve-retire\n"
        f"target_branch: {observation.lane_ref}\n"
        f"target_head: {observation.head}\n"
        "---\n",
        "record carrier-only target binding",
    )

    planned = _plan(carrier, chronicle_ref=chronicle_ref)

    assert planned["ok"] is False
    assert planned["required_gaps"] == ["lane_resolution_chronicle_missing"]


def test_preserve_retire_rechecks_chronicle_after_preservation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    (lane / "README.md").write_text("# preserve then bind\n", encoding="utf-8")
    chronicle_ref = _bound_chronicle(repo, branch="work/orphan")
    planned = _plan(repo, chronicle_ref=chronicle_ref)
    original = recovery_adapter.prepare_resolution_effect

    def replace_chronicle(
        **kwargs: object,
    ) -> tuple[dict[str, object], dict[str, object], str, str]:
        result = original(**kwargs)
        _bound_chronicle(
            repo,
            branch="work/orphan",
            relative=chronicle_ref,
            binding=_ChronicleBinding(revision="two"),
        )
        return result

    monkeypatch.setattr(recovery_adapter, "prepare_resolution_effect", replace_chronicle)

    applied = apply_lane_resolution(
        root=repo,
        decision_path=Path(str(planned["decision_path"])),
        confirm_irreversible=True,
        apply=True,
    )

    assert planned["ok"] is True
    assert applied["ok"] is False
    assert applied["required_gaps"] == ["lane_resolution_chronicle_stale"]
    assert lane.is_dir()


def test_preserve_retire_rechecks_chronicle_after_final_target_observation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    chronicle_ref = _bound_chronicle(repo, branch="work/orphan")
    planned = _plan(repo, chronicle_ref=chronicle_ref)
    original_observe = recovery_adapter.observe_lane

    def drift_after_final_observation(
        root: Path,
        branch: str,
    ) -> tuple[LaneObservation, list[str]]:
        current, gaps = original_observe(root, branch)
        _bound_chronicle(
            repo,
            branch="work/orphan",
            relative=chronicle_ref,
            binding=_ChronicleBinding(revision="after-final-observation"),
        )
        return current, gaps

    monkeypatch.setattr(recovery_adapter, "observe_lane", drift_after_final_observation)

    applied = apply_lane_resolution(
        root=repo,
        decision_path=Path(str(planned["decision_path"])),
        confirm_irreversible=True,
        apply=True,
    )

    assert lane.is_dir()
    assert applied["ok"] is False
    assert applied["required_gaps"] == ["lane_resolution_chronicle_stale"]
    assert applied["receipt"]["state"] == "preserved_retirement_blocked"
    assert applied["receipt"]["retirement_blocked_reason"] == "lane_resolution_chronicle_stale"


def test_post_package_chronicle_drift_retains_a_valid_clearable_preservation_record(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    chronicle_ref = _bound_chronicle(repo, branch="work/orphan")
    planned = _plan(repo, chronicle_ref=chronicle_ref)
    original = recovery_adapter.prepare_resolution_effect

    def replace_chronicle(
        **kwargs: object,
    ) -> tuple[dict[str, object], dict[str, object], str, str]:
        result = original(**kwargs)
        _bound_chronicle(
            repo,
            branch="work/orphan",
            relative=chronicle_ref,
            binding=_ChronicleBinding(revision="retained-package"),
        )
        return result

    monkeypatch.setattr(recovery_adapter, "prepare_resolution_effect", replace_chronicle)

    applied = apply_lane_resolution(
        root=repo,
        decision_path=Path(str(planned["decision_path"])),
        confirm_irreversible=True,
        apply=True,
    )

    assert applied["ok"] is False
    assert applied["required_gaps"] == ["lane_resolution_chronicle_stale"]
    assert lane.is_dir()
    assert applied["receipt"]["state"] == "preserved_retirement_blocked"
    assert applied["receipt"]["retirement_blocked_reason"] == "lane_resolution_chronicle_stale"
    inventory = lane_resolution_inventory(root=repo)
    assert inventory["ok"] is True
    entry = inventory["entries"][0]
    assert entry["state"] == "preserved_retirement_blocked"
    assert entry["retirement_blocked_reason"] == "lane_resolution_chronicle_stale"

    clear_chronicle_ref = "evidence/chronicle/target-binding/clear-retained-package.md"
    commit_fixture_file(
        repo,
        clear_chronicle_ref,
        "event: lane_resolution/clear-preservation\n",
        "authorize retained package clear",
    )
    clear = clear_lane_resolution_package(
        root=repo,
        request=LaneResolutionClearRequest(
            decision_id=str(planned["decision"]["decision_id"]),
            expect_manifest_sha256=str(entry["manifest_sha256"]),
            chronicle_ref=clear_chronicle_ref,
            reason="Retained preservation bytes are explicitly clearable.",
            break_glass=True,
            confirm_irreversible=True,
            apply=False,
        ),
    )

    assert clear["ok"] is True
    assert clear["state"] == "planned"

    monkeypatch.undo()
    next_chronicle_ref = _bound_chronicle(
        repo,
        branch="work/orphan",
        relative="evidence/chronicle/target-binding/fresh-decision.md",
    )
    next_planned = _plan(repo, chronicle_ref=next_chronicle_ref)
    next_applied = apply_lane_resolution(
        root=repo,
        decision_path=Path(str(next_planned["decision_path"])),
        confirm_irreversible=True,
        apply=True,
    )

    assert next_planned["ok"] is True
    assert next_applied["ok"] is True
    assert not lane.exists()


def test_post_package_target_drift_records_preserved_retirement_blocked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    chronicle_ref = _bound_chronicle(repo, branch="work/orphan")
    planned = _plan(repo, chronicle_ref=chronicle_ref)
    original_observe = recovery_adapter.observe_lane

    def stale_final_observation(
        root: Path,
        branch: str,
    ) -> tuple[LaneObservation, list[str]]:
        current, gaps = original_observe(root, branch)
        return current.model_copy(update={"tracked_digest": "f" * 64}), gaps

    monkeypatch.setattr(recovery_adapter, "observe_lane", stale_final_observation)

    applied = apply_lane_resolution(
        root=repo,
        decision_path=Path(str(planned["decision_path"])),
        confirm_irreversible=True,
        apply=True,
    )

    assert applied["ok"] is False
    assert applied["required_gaps"] == ["lane_resolution_observation_stale"]
    assert lane.is_dir()
    assert applied["receipt"]["state"] == "preserved_retirement_blocked"
    assert applied["receipt"]["retirement_blocked_reason"] == "lane_resolution_observation_stale"


def test_blocked_retirement_receipt_without_its_package_is_current_record_invalid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    chronicle_ref = _bound_chronicle(repo, branch="work/orphan")
    planned = _plan(repo, chronicle_ref=chronicle_ref)
    original = recovery_adapter.prepare_resolution_effect

    def replace_chronicle(
        **kwargs: object,
    ) -> tuple[dict[str, object], dict[str, object], str, str]:
        result = original(**kwargs)
        _bound_chronicle(
            repo,
            branch="work/orphan",
            relative=chronicle_ref,
            binding=_ChronicleBinding(revision="missing-package"),
        )
        return result

    monkeypatch.setattr(recovery_adapter, "prepare_resolution_effect", replace_chronicle)
    applied = apply_lane_resolution(
        root=repo,
        decision_path=Path(str(planned["decision_path"])),
        confirm_irreversible=True,
        apply=True,
    )
    package = Path(str(applied["preservation_package"]["path"]))
    package.rename(tmp_path / "removed-preservation-package")

    inventory = lane_resolution_inventory(root=repo)

    assert applied["receipt"]["state"] == "preserved_retirement_blocked"
    assert lane.is_dir()
    assert inventory["ok"] is False
    assert inventory["summary"]["invalid_current_record_count"] == 1
    assert "lane_resolution_current_record_invalid" in inventory["required_gaps"]
