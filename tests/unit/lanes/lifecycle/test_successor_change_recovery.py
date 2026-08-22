from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING
from typing import cast

import pytest

import ethos.adapters.mutation.lane_lifecycle.successor_change as successor_change
import ethos.adapters.openspec.change_lineage.successor_commitment as successor_commitment
import ethos.adapters.openspec.generation.attestation as generation_attestation
from ethos.adapters.repo.native_effect_attestation import NativeEffect
from ethos.adapters.repo.native_effect_attestation import issue_native_effect
from ethos.adapters.store.state.lease.projection import project_lease
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_test_profile
from tests.support.lifecycle_cases import strict_lease

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Attestation


BRANCH = "work/feature"
HEAD = "a" * 40
NEW_HEAD = "b" * 40
OLD_TREE = "c" * 40
NEW_TREE = "e" * 40
HOLDER = "agent:test:case:holder"
ARCHIVE = "openspec/changes/archive/2026-08-10-finished/commitment.toml"
CHANGE = "next-change"


def _lease(**updates: object) -> dict[str, object]:
    lease: dict[str, object] = {
        "lease_state": "valid",
        "holder_ref": HOLDER,
        "expected_head": HEAD,
        "expected_tree": OLD_TREE,
        "base_commitment_path": ARCHIVE,
        "lease_id": "lease:1",
        "epoch": 1,
        "expires_at": "2026-08-11T00:00:00+00:00",
        "payload_sha256": "d" * 64,
    }
    lease.update(updates)
    return lease


def _common(monkeypatch: pytest.MonkeyPatch, lease: dict[str, object] | None = None) -> None:
    monkeypatch.setenv("ETHOS_ACTOR", HOLDER)
    monkeypatch.setattr(successor_change, "git_stdout", lambda *_args, **_kwargs: BRANCH)
    monkeypatch.setattr(generation_attestation, "git_stdout", lambda *_args, **_kwargs: BRANCH)
    for module in (successor_change, successor_commitment, generation_attestation):
        monkeypatch.setattr(module, "current_tracked_head", lambda _root: HEAD)
    for module in (successor_commitment, generation_attestation):
        monkeypatch.setattr(
            module,
            "first_parent_successor",
            lambda _root, ancestor, descendant: (
                NEW_HEAD if (ancestor, descendant) == (HEAD, NEW_HEAD) else ""
            ),
        )
    monkeypatch.setattr(
        successor_change,
        "leases_by_branch",
        lambda _root: {BRANCH: lease or _lease()},
    )
    monkeypatch.setattr(generation_attestation, "read_attestation_set", lambda _root: ("", ()))
    monkeypatch.setattr(
        successor_change,
        "work_lane_transition_gaps",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(
        successor_change,
        "change_overlay_report",
        lambda *_args, **_kwargs: {"paths": (), "digest": "", "required_gaps": []},
    )
    for module in (successor_change, successor_commitment, generation_attestation):
        monkeypatch.setattr(
            module,
            "load_repository_commitment",
            lambda *_args, **_kwargs: SimpleNamespace(id="repository:test"),
        )
    monkeypatch.setattr(
        successor_change,
        "load_lease_bound_commitment",
        lambda *_args, **_kwargs: SimpleNamespace(digest=lambda: "f" * 64),
    )
    for module in (successor_change, successor_commitment, generation_attestation):
        monkeypatch.setattr(
            module, "load_commitment", lambda *_args, **_kwargs: _change_commitment()
        )
    monkeypatch.setattr(generation_attestation, "record_attestation_once", lambda _root, item: item)
    monkeypatch.setattr(successor_change, "state_database", lambda root: root / "state.sqlite")
    monkeypatch.setattr(
        successor_change.openspec_cli,
        "openspec_base_command",
        lambda: ("openspec",),
    )
    monkeypatch.setattr(
        successor_change.openspec_cli,
        "run_json",
        lambda *_args, **_kwargs: {"exit_code": 0, "parse_error": "", "json": {"changes": []}},
    )
    monkeypatch.setattr(
        successor_change,
        "lifecycle_commit_subject",
        lambda *_args, **_kwargs: "chore(openspec): start next-change",
    )


def _start(root: Path, *, apply: bool = False) -> dict[str, object]:
    return successor_change.start_change(
        root=root,
        change=CHANGE,
        intent="Continue exact governed work.",
        scope=("src/**",),
        expect_head=HEAD,
        apply=apply,
    )


def test_change_start_commit_subject_is_conventional(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    write_test_profile(repo)
    assert successor_change.lifecycle_commit_subject(repo, "start", CHANGE) == (
        "chore(openspec): start next-change"
    )


def _branch_status(_root: Path, *args: str, **_kwargs: object) -> str:
    if args[:2] == ("branch", "--show-current"):
        return BRANCH
    if "--format=%ct" in args:
        return "1786791600"
    if args[-1:] == (f"{NEW_HEAD}^",):
        return HEAD
    if args[-1:] == (f"{HEAD}^{{tree}}",):
        return OLD_TREE
    if args[-1:] == (f"{NEW_HEAD}^{{tree}}",):
        return NEW_TREE
    return ""


def _observe_new_head(monkeypatch: pytest.MonkeyPatch) -> None:
    for module in (successor_change, generation_attestation):
        monkeypatch.setattr(module, "current_tracked_head", lambda _root: NEW_HEAD)
    monkeypatch.setattr(
        generation_attestation,
        "git_stdout",
        lambda _root, *args: HEAD if args[:2] == ("rev-parse", f"{NEW_HEAD}^") else "",
    )


def _prepare_recovery(
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
    lease: dict[str, object],
    *,
    target_tree: str = NEW_TREE,
) -> None:
    old_model = strict_lease(
        branch=BRANCH,
        holder=HOLDER,
        expected_head=HEAD,
        expected_tree=OLD_TREE,
        base_commitment_path=ARCHIVE,
    )
    old_lease = project_lease(old_model)
    current_lease = project_lease(
        old_model.model_copy(
            update={
                "expected_head": str(lease["expected_head"]),
                "expected_tree": str(lease["expected_tree"]),
            }
        )
    )
    old = successor_change.lease_generation(old_lease)
    commitment = _change_commitment()
    effect = NativeEffect(
        predicate="effect:openspec-change-start-prepared",
        operation="openspec.change.start",
        command=("openspec", "new", "change", CHANGE, "--json"),
        subject={"change": CHANGE, "previous_head": HEAD, "tree": target_tree},
        before={"head": HEAD, "lease": old},
        after={
            "tree": target_tree,
            "commitment_path": f"openspec/changes/{CHANGE}/commitment.toml",
            "commitment_digest": commitment.digest(),
            "predecessors": list(commitment.predecessors),
        },
    )
    witness = issue_native_effect(
        root,
        effect=effect,
        state="prepared",
        commitment_digest=commitment.digest(),
        repository_id="repository:test",
    )
    _common(monkeypatch, current_lease)
    for module in (successor_change, generation_attestation):
        monkeypatch.setattr(module, "current_tracked_head", lambda _root: NEW_HEAD)
    monkeypatch.setattr(
        generation_attestation,
        "current_tree",
        lambda _root, ref: OLD_TREE if ref == HEAD else target_tree,
    )
    monkeypatch.setattr(
        generation_attestation, "read_attestation_set", lambda _root: ("", (witness,))
    )
    monkeypatch.setattr(
        generation_attestation, "load_commitment", lambda *_args, **_kwargs: commitment
    )
    target = {
        "expected_head": NEW_HEAD,
        "expected_tree": target_tree,
        "base_commitment_path": f"openspec/changes/{CHANGE}/commitment.toml",
        "base_commitment_bytes_sha256": "a" * 64,
        "base_commitment_digest": commitment.digest(),
    }
    for module in (successor_change, generation_attestation):
        monkeypatch.setattr(module, "exact_commitment_fields", lambda *_args, **_kwargs: target)


def _change_commitment() -> SimpleNamespace:
    return SimpleNamespace(
        intent="Continue exact governed work.",
        scope=(f"openspec/changes/{CHANGE}/**", "src/**"),
        predecessors=("f" * 64,),
        selected_attestations=(),
        digest=lambda: "e" * 64,
    )


def _recognized_attestation(
    root: Path,
    *,
    change: str,
    previous_head: str,
    head: str,
) -> Attestation:
    old = _lease(base_commitment_digest="f" * 64)
    new = _lease(
        expected_head=head,
        expected_tree=NEW_TREE,
        base_commitment_path=f"openspec/changes/{change}/commitment.toml",
        base_commitment_digest="e" * 64,
        epoch=2,
    )
    return issue_native_effect(
        root,
        effect=NativeEffect(
            predicate="effect:openspec-change-start",
            operation="openspec.change.start",
            command=("openspec", "new", "change", change, "--json"),
            subject={"change": change, "previous_head": previous_head, "head": head},
            before={"head": previous_head, "lease": old},
            after={"head": head, "lease": new, "predecessors": ["f" * 64]},
        ),
        state="recognized",
        commitment_digest="e" * 64,
        repository_id="repository:test",
    )


def test_start_change_public_recovery_dry_run_and_finish_failure_are_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lease = _lease(expected_head=NEW_HEAD, expected_tree=NEW_TREE)
    _prepare_recovery(monkeypatch, tmp_path, lease)
    monkeypatch.setattr(successor_change, "git_stdout", _branch_status)
    monkeypatch.setattr(generation_attestation, "git_stdout", _branch_status)
    ready = _start(tmp_path)
    assert (ready["verdict"], ready["state"]) == ("pass", "ready_to_recover"), ready

    monkeypatch.setattr(
        successor_change,
        "local_state_mutation_guard",
        lambda _root: {"required_gaps": []},
    )
    monkeypatch.setattr(
        successor_change,
        "rebind_lease_commitment",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("commitment_rebind_failed")),
    )
    failed = _start(tmp_path, apply=True)
    assert failed["required_gaps"] == ["commitment_rebind_failed"]
    assert failed["state"] == "repair_required"


def test_prepared_recovery_rejects_current_lease_tree_not_bound_to_head(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    current = _lease(expected_head=NEW_HEAD, expected_tree="d" * 40)
    _prepare_recovery(monkeypatch, tmp_path, current, target_tree="f" * 40)

    def observed(_root: Path, *args: str, **_kwargs: object) -> str:
        if args[:2] == ("branch", "--show-current"):
            return BRANCH
        if args[-1:] == (f"{NEW_HEAD}^",):
            return HEAD
        if args[-1:] == (f"{HEAD}^{{tree}}",):
            return OLD_TREE
        if args[-1:] == (f"{NEW_HEAD}^{{tree}}",):
            return "f" * 40
        return ""

    monkeypatch.setattr(successor_change, "git_stdout", observed)
    monkeypatch.setattr(generation_attestation, "git_stdout", observed)
    monkeypatch.setattr(
        generation_attestation,
        "current_tree",
        lambda _root, ref: OLD_TREE if ref == HEAD else "f" * 40,
    )

    report = _start(tmp_path)

    assert report["required_gaps"] == ["openspec_change_start_attestation_collision"]
    assert report["state"] == "repair_required"


def test_start_change_recovery_guard_falls_back_to_public_preflight(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lease = _lease(expected_head=NEW_HEAD, expected_tree=NEW_TREE)
    _prepare_recovery(monkeypatch, tmp_path, lease)
    monkeypatch.setattr(successor_change, "git_stdout", _branch_status)
    monkeypatch.setattr(generation_attestation, "git_stdout", _branch_status)
    monkeypatch.setattr(
        successor_change,
        "local_state_mutation_guard",
        lambda _root: {
            "required_gaps": ["local_state_migration_required"],
            "next_action": "ethos state migrate --json",
        },
    )
    monkeypatch.setattr(
        successor_change,
        "work_lane_transition_gaps",
        lambda *_args, **_kwargs: ["preflight_would_have_run"],
    )

    report = _start(tmp_path, apply=True)

    assert report["required_gaps"] == ["preflight_would_have_run"]


def test_start_change_apply_guard_replaces_public_preflight_authority_gaps(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _common(monkeypatch)
    monkeypatch.setattr(
        successor_change,
        "local_state_mutation_guard",
        lambda _root: {
            "required_gaps": ["local_state_authority_mismatch"],
            "next_action": "ethos state reconcile --json",
        },
    )

    report = _start(tmp_path, apply=True)

    assert report["required_gaps"] == ["local_state_authority_mismatch"]
    assert report["next_action"] == "ethos state reconcile --json"


@pytest.mark.parametrize(
    ("case", "gap"),
    [
        ("commitment", "lease_commitment_invalid"),
        ("missing-cli", "openspec_official_cli_missing"),
        ("unreadable-list", "openspec_list_unreadable"),
        ("active-list", "openspec_active_change_present"),
    ],
)
def test_start_change_public_preflight_rejects_invalid_generation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case: str,
    gap: str,
) -> None:
    _common(monkeypatch)
    if case == "commitment":
        monkeypatch.setattr(
            successor_change,
            "load_lease_bound_commitment",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError(gap)),
        )
    else:
        monkeypatch.setattr(
            successor_change.openspec_cli,
            "openspec_base_command",
            lambda: None if case == "missing-cli" else ("openspec",),
        )
        monkeypatch.setattr(
            successor_change.openspec_cli,
            "run_json",
            lambda *_args, **_kwargs: {
                "exit_code": 1 if case == "unreadable-list" else 0,
                "parse_error": "",
                "json": {
                    "changes": []
                    if case == "unreadable-list"
                    else [
                        {
                            "name": "unfinished",
                            "status": "no-tasks",
                            "completedTasks": 0,
                            "totalTasks": 0,
                        }
                    ]
                },
            },
        )

    report = _start(tmp_path)

    assert report["required_gaps"] == [gap]


@pytest.mark.parametrize("case", ["missing-cli", "invalid-result", "commit-failed"])
def test_start_change_public_apply_compensates_partial_creation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case: str,
) -> None:
    _common(monkeypatch)
    monkeypatch.setattr(
        successor_change,
        "local_state_mutation_guard",
        lambda _root: {"required_gaps": []},
    )
    calls = iter((("list", "--json"), ("new", "change", CHANGE, "--json")))
    change_root = tmp_path / f"openspec/changes/{CHANGE}"
    monkeypatch.setattr(
        successor_change.openspec_cli,
        "openspec_base_command",
        lambda: None if case == "missing-cli" else ("openspec",),
    )

    def run_json(_root: Path, _command: tuple[str, ...], args: tuple[str, ...]):
        expected = next(calls)
        assert args == expected
        if args[0] == "list":
            return {"exit_code": 0, "parse_error": "", "json": {"changes": []}}
        change_root.mkdir(parents=True)
        (change_root / ".openspec.yaml").write_text("schema: spec-driven\n", encoding="utf-8")
        return {
            "command": ["openspec", *args],
            "exit_code": 0,
            "parse_error": "",
            "json": {
                "change": {
                    "id": CHANGE if case != "invalid-result" else "other",
                    "path": change_root.as_posix(),
                }
            },
        }

    monkeypatch.setattr(successor_change.openspec_cli, "run_json", run_json)
    removed: list[str] = []
    compensated: list[str] = []
    monkeypatch.setattr(
        successor_change,
        "remove_untracked_tree",
        lambda _root, path: removed.append(path),
    )
    monkeypatch.setattr(successor_change, "stage_git_paths", lambda *_args: None)
    monkeypatch.setattr(
        successor_change,
        "commit_git_worktree",
        lambda *_args, **_kwargs: {"verdict": "block" if case == "commit-failed" else "pass"},
    )
    monkeypatch.setattr(
        successor_change,
        "compensate_created_paths",
        lambda *_args, **_kwargs: compensated.append("compensated"),
    )

    report = _start(tmp_path, apply=True)

    expected = {
        "missing-cli": "openspec_official_cli_missing",
        "invalid-result": "openspec_change_create_failed",
        "commit-failed": "openspec_change_commit_failed",
    }[case]
    assert report["required_gaps"] == [expected]
    assert bool(removed) is (case == "invalid-result")
    assert bool(compensated) is (case == "commit-failed")


def test_start_change_public_reader_skips_corrupt_receipt_and_invalid_target(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lease = _lease(expected_head=NEW_HEAD)
    _common(monkeypatch, lease)
    store = tmp_path / "attestations"
    store.mkdir()
    (store / "corrupt.json").write_text("not-json", encoding="utf-8")
    _observe_new_head(monkeypatch)
    monkeypatch.setattr(
        generation_attestation,
        "exact_commitment_fields",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("invalid target")),
    )
    monkeypatch.setattr(
        successor_change,
        "work_lane_transition_gaps",
        lambda *_args, **_kwargs: ["not_recoverable"],
    )
    report = _start(tmp_path)

    assert report["required_gaps"] == ["not_recoverable"]


def test_start_change_public_reader_recognizes_exact_receipt(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    carrier = f"openspec/changes/{CHANGE}/commitment.toml"
    lease = _lease(expected_head=NEW_HEAD, base_commitment_path=carrier)
    _common(monkeypatch, lease)
    attestation = _recognized_attestation(
        tmp_path,
        change=CHANGE,
        previous_head=HEAD,
        head=NEW_HEAD,
    )
    _observe_new_head(monkeypatch)
    monkeypatch.setattr(
        successor_change,
        "work_lane_transition_gaps",
        lambda *_args, **_kwargs: ["not_recoverable"],
    )
    monkeypatch.setattr(
        generation_attestation,
        "load_repository_commitment",
        lambda *_args, **_kwargs: SimpleNamespace(id="repository:test"),
    )
    monkeypatch.setattr(
        generation_attestation,
        "start_effect_authority",
        lambda *_args, **_kwargs: {"predicate": "effect:openspec-change-start"},
    )

    report = _start(tmp_path)

    assert report["state"] != "recognized"
    assert "openspec_archived_commitment_required" in cast("list[str]", report["required_gaps"])
    monkeypatch.setattr(
        generation_attestation,
        "read_attestation_set",
        lambda _root: ("selected", (attestation,)),
    )
    report = _start(tmp_path)
    assert report["state"] == "recognized"
    attestation_report = cast("dict[str, object]", report["attestation"])
    assert attestation_report["predicate"] == "effect:openspec-change-start"
