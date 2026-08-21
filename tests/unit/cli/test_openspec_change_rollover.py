from __future__ import annotations

import os
import subprocess
import tomllib
from datetime import UTC
from datetime import datetime
from pathlib import Path

import pytest

import ethos.adapters.mutation.lane_lifecycle.change_rollover as rollover
import ethos.adapters.openspec.lifecycle.intent as lifecycle_intent
from ethos.adapters.admission.prewrite import prewrite_guard
from ethos.adapters.mutation.lane_lifecycle.change_rollover import start_change
from ethos.adapters.repo.attestation_set import ATTESTATION_SET_REF
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.dirty.change_provenance import dirty_content_sha256
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.contracts.semantic import Attestation
from ethos.normalization.coercion import integer
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import git
from tests.support.openspec_lifecycle import OpenSpecLifecycle
from tests.support.openspec_lifecycle import completed_lifecycle
from tools.ci.delivery.pipeline import DeliveryPipeline
from tools.ci.toolchain.environment import ProjectRuntime

ROOT = Path(__file__).resolve().parents[3]
RUNTIME = ProjectRuntime.discover(ROOT)
TAPLO = ROOT / "node_modules/@taplo/cli/dist/cli.js"


def _archived_lane(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> OpenSpecLifecycle:
    lifecycle = completed_lifecycle(tmp_path, monkeypatch)
    archived = lifecycle.apply_archive()
    assert archived["verdict"] == "pass", archived
    return lifecycle


def _selection_pair(
    change: str,
    *,
    valid_until: datetime | None = None,
) -> tuple[Attestation, Attestation]:
    occurrence = Attestation.issue(
        {
            "schema_version": 2,
            "predicate": "observation:feedback",
            "verifier": "agent:test:intent-promotion",
            "subject": f"input:occurrence:{change}",
            "issued_at": datetime(2026, 8, 15, tzinfo=UTC),
            "valid_from": None,
            "valid_until": None,
            "verdict": "pass",
            "payload": {"kind": "input:feedback", "body": {"occurrence": {"ordinal": 1}}},
            "relations": (),
            "advisories": (),
            "evidence_refs": (f"evidence:test:{change}",),
            "commitment_digest": None,
            "facts_digest": None,
            "plan_digest": None,
            "policy_digest": None,
            "effect_digest": None,
            "mints_authority": False,
        }
    )
    owner = f"change:{change}"
    selection = Attestation.issue(
        {
            "schema_version": 2,
            "predicate": "selection:input",
            "verifier": "agent:test:intent-promotion",
            "subject": occurrence.id,
            "issued_at": datetime(2026, 8, 15, tzinfo=UTC),
            "valid_from": None,
            "valid_until": valid_until,
            "verdict": "pass",
            "payload": {
                "kind": "selection:disposition",
                "body": {"disposition": "semantic-owner", "owner": owner},
            },
            "relations": (
                {
                    "kind": "relation:disposes",
                    "target_kind": "semantic:attestation",
                    "target_id": occurrence.id,
                    "attributes": {},
                },
                {
                    "kind": "relation:selected-for",
                    "target_kind": "semantic:commitment",
                    "target_id": owner,
                    "attributes": {},
                },
            ),
            "advisories": (),
            "evidence_refs": (occurrence.id,),
            "commitment_digest": None,
            "facts_digest": None,
            "plan_digest": None,
            "policy_digest": None,
            "effect_digest": None,
            "mints_authority": False,
        }
    )
    return occurrence, selection


def test_start_change_rolls_an_archived_owned_lane_to_a_new_commitment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lifecycle = _archived_lane(tmp_path, monkeypatch)
    worktree, branch, previous_lease = (
        lifecycle.worktree,
        lifecycle.branch,
        lifecycle.lease,
    )
    archived_head = current_tracked_head(worktree)

    report = start_change(
        root=worktree,
        change="hosted-verification-fix",
        intent="Repair hosted verification without reopening archived work.",
        scope=("tests/**",),
        expect_head=archived_head,
        apply=True,
    )

    current = current_tracked_head(worktree)
    lease = leases_by_branch(worktree)[branch]
    assert report["verdict"] == "pass", report
    assert report["state"] == "started"
    assert report["previous_head"] == archived_head
    assert report["head"] == current
    assert current != archived_head
    assert lease["expected_head"] == current
    assert lease["base_commitment_path"] == (
        "openspec/changes/hosted-verification-fix/commitment.toml"
    )
    assert integer(lease["epoch"]) == integer(previous_lease["epoch"]) + 1
    assert git(worktree, "status", "--short") == ""
    commitment = worktree / "openspec/changes/hosted-verification-fix/commitment.toml"
    commitment_text = commitment.read_text(encoding="utf-8")
    assert tomllib.loads(commitment_text) == {
        "schema_version": 2,
        "id": "change:hosted-verification-fix",
        "intent": "Repair hosted verification without reopening archived work.",
        "subjects": [load_repository_commitment(worktree).id],
        "scope": ["openspec/changes/hosted-verification-fix/**", "tests/**"],
        "invariants": [],
        "acceptance": [],
        "risks": [],
        "authority_refs": [],
        "predecessors": [load_lease_bound_commitment(worktree, lease=previous_lease).digest()],
        "selected_attestations": [],
        "dependencies": [],
        "hypotheses": [],
        "falsifiers": [],
        "experiment_protocols": [],
    }
    assert "repository:self" not in commitment_text
    assert (
        subprocess.run(
            (
                str(DeliveryPipeline.from_runtime(RUNTIME).node),
                str(TAPLO),
                "format",
                "--check",
                "--config",
                str(ROOT / ".config/checks/taplo/taplo.toml"),
                str(commitment),
            ),
            cwd=worktree,
            check=False,
            capture_output=True,
        ).returncode
        == 0
    )
    assert (
        prewrite_guard(
            root=worktree,
            paths=[worktree / "tests/governance/test_repository.py"],
            editor_root=worktree,
            require_editor_root=True,
        )["verdict"]
        == "pass"
    )


def test_start_change_binds_only_selected_input_disposed_to_the_successor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lifecycle = _archived_lane(tmp_path, monkeypatch)
    worktree = lifecycle.worktree
    archived_head = current_tracked_head(worktree)
    predecessor_digest = load_lease_bound_commitment(worktree, lease=lifecycle.lease).digest()
    occurrence, selection = _selection_pair("hosted-verification-fix")
    record_attestations(worktree, (occurrence, selection))

    report = start_change(
        root=worktree,
        change="hosted-verification-fix",
        intent="Repair hosted verification.",
        scope=("tests/**",),
        expect_head=archived_head,
        selected_attestations=(selection.id,),
        apply=True,
    )

    assert report["verdict"] == "pass", report
    carrier = tomllib.loads(
        (worktree / "openspec/changes/hosted-verification-fix/commitment.toml").read_text(
            encoding="utf-8"
        )
    )
    assert carrier["selected_attestations"] == [selection.id]
    assert carrier["predecessors"] == [predecessor_digest]


def test_start_change_apply_preserves_selected_set_addition_after_preflight(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worktree = _archived_lane(tmp_path, monkeypatch).worktree
    archived_head = current_tracked_head(worktree)
    occurrence, selection = _selection_pair("selected-set-replacement")
    record_attestations(worktree, (occurrence, selection))
    _root, before = read_attestation_set(worktree)
    before_ids = {item.id for item in before}
    external = occurrence.model_copy(
        update={
            "id": "",
            "subject": "input:occurrence:external-concurrent-addition",
            "evidence_refs": ("evidence:test:external-concurrent-addition",),
        }
    )
    external = Attestation.issue(external.model_dump(mode="python", exclude={"id"}))
    original = rollover.openspec_cli.run_json

    def replace_selected_set(root: Path, command: tuple[str, ...], arguments: tuple[str, ...]):
        if arguments[:2] == ("new", "change"):
            record_attestations(worktree, (external,))
        return original(root, command, arguments)

    monkeypatch.setattr(rollover.openspec_cli, "run_json", replace_selected_set)

    report = start_change(
        root=worktree,
        change="selected-set-replacement",
        intent="Bind the selected Attestation set through mutation.",
        scope=("tests/**",),
        expect_head=archived_head,
        selected_attestations=(selection.id,),
        apply=True,
    )

    assert report["verdict"] == "block", report
    assert report["required_gaps"] == ["selected_attestation_set_changed"]
    assert current_tracked_head(worktree) == archived_head
    assert not (worktree / "openspec/changes/selected-set-replacement").exists()
    _root, current = read_attestation_set(worktree)
    assert {item.id for item in current} == before_ids | {external.id}


def test_start_change_apply_rejects_selection_expired_after_preflight(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worktree = _archived_lane(tmp_path, monkeypatch).worktree
    archived_head = current_tracked_head(worktree)
    before = datetime(2026, 8, 15, tzinfo=UTC)
    after = datetime(2026, 8, 15, 0, 0, 2, tzinfo=UTC)
    occurrence, selection = _selection_pair(
        "selection-expiry",
        valid_until=datetime(2026, 8, 15, 0, 0, 1, tzinfo=UTC),
    )
    record_attestations(worktree, (occurrence, selection))

    class Clock:
        calls = 0

        @classmethod
        def now(cls, _timezone):
            cls.calls += 1
            return before if cls.calls == 1 else after

    monkeypatch.setattr(lifecycle_intent, "datetime", Clock)

    report = start_change(
        root=worktree,
        change="selection-expiry",
        intent="Revalidate selection freshness through mutation.",
        scope=("tests/**",),
        expect_head=archived_head,
        selected_attestations=(selection.id,),
        apply=True,
    )

    assert report["verdict"] == "block", report
    assert report["required_gaps"] == [f"selected_attestation_disposition_invalid:{selection.id}"]
    assert current_tracked_head(worktree) == archived_head
    assert not (worktree / "openspec/changes/selection-expiry").exists()


def test_start_change_rejects_an_unselected_or_wrongly_disposed_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lifecycle = _archived_lane(tmp_path, monkeypatch)
    worktree = lifecycle.worktree
    archived_head = current_tracked_head(worktree)

    report = start_change(
        root=worktree,
        change="hosted-verification-fix",
        intent="Repair hosted verification.",
        scope=("tests/**",),
        expect_head=archived_head,
        selected_attestations=("f" * 64,),
        apply=True,
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == [f"selected_attestation_missing:{'f' * 64}"]
    assert current_tracked_head(worktree) == archived_head


@pytest.mark.parametrize(
    ("label", "update"),
    [
        ("blocked", {"verdict": "block"}),
        ("future", {"valid_from": datetime(2100, 1, 1, tzinfo=UTC)}),
        ("expired", {"valid_until": datetime(2021, 1, 1, tzinfo=UTC)}),
    ],
)
def test_selection_freshness_rejects_non_current_attestation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    label: str,
    update: dict[str, object],
) -> None:
    change = f"freshness-{label}"
    lifecycle = _archived_lane(tmp_path, monkeypatch)
    worktree = lifecycle.worktree
    occurrence, selection = _selection_pair(change)
    payload = selection.model_dump(mode="python", exclude={"id"}) | update
    invalid = Attestation.issue(payload)
    record_attestations(worktree, (occurrence, invalid))

    report = start_change(
        root=worktree,
        change=change,
        intent="Reject a non-current selected Attestation.",
        scope=("tests/**",),
        expect_head=current_tracked_head(worktree),
        selected_attestations=(invalid.id,),
        apply=True,
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == [f"selected_attestation_disposition_invalid:{invalid.id}"]


def test_start_change_rejects_a_different_holder_without_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worktree = _archived_lane(tmp_path, monkeypatch).worktree
    archived_head = current_tracked_head(worktree)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:different")

    report = start_change(
        root=worktree,
        change="hosted-verification-fix",
        intent="Repair hosted verification.",
        scope=("tests/**",),
        expect_head=archived_head,
        apply=True,
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["lease_actor_mismatch"]
    assert current_tracked_head(worktree) == archived_head
    assert not (worktree / "openspec/changes/hosted-verification-fix").exists()


def test_start_change_rejects_a_dirty_overlay_without_an_exact_digest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worktree = _archived_lane(tmp_path, monkeypatch).worktree
    archived_head = current_tracked_head(worktree)
    target = worktree / "tests/governance/test_repository.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("forward fix\n", encoding="utf-8")
    git(worktree, "add", target.relative_to(worktree).as_posix())

    report = start_change(
        root=worktree,
        change="hosted-verification-fix",
        intent="Repair hosted verification.",
        scope=("tests/**",),
        expect_head=archived_head,
        apply=True,
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["openspec_change_overlay_digest_required"]
    assert current_tracked_head(worktree) == archived_head
    assert git(worktree, "status", "--short")


def test_start_change_cli_commits_an_exact_scope_bound_staged_overlay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lifecycle = _archived_lane(tmp_path, monkeypatch)
    worktree, branch, previous_lease = (
        lifecycle.worktree,
        lifecycle.branch,
        lifecycle.lease,
    )
    archived_head = current_tracked_head(worktree)
    target = worktree / "tests/governance/test_repository.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("def test_forward_fix():\n    assert True\n", encoding="utf-8")
    git(worktree, "add", target.relative_to(worktree).as_posix())

    payload = run_ethos(
        *_start_change_arguments(
            worktree,
            archived_head,
            "--expected-overlay-digest",
            dirty_content_sha256(worktree),
        ),
        cwd=worktree,
    )

    current = current_tracked_head(worktree)
    lease = leases_by_branch(worktree)[branch]
    assert payload["state"] == "started"
    assert git(worktree, "show", f"{current}:tests/governance/test_repository.py")
    assert lease["expected_head"] == current
    assert integer(lease["epoch"]) == integer(previous_lease["epoch"]) + 1
    assert git(worktree, "status", "--short") == ""


def test_start_change_cli_rejects_an_unsafe_scope_before_official_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worktree = _archived_lane(tmp_path, monkeypatch).worktree
    archived_head = current_tracked_head(worktree)

    payload = run_ethos_blocked(
        *_start_change_arguments(worktree, archived_head, scope="../outside/**"),
        cwd=worktree,
    )

    assert payload["required_gaps"] == ["openspec_change_commitment_invalid"]
    assert current_tracked_head(worktree) == archived_head
    assert not (worktree / "openspec/changes/hosted-verification-fix").exists()


def test_start_change_cli_recognizes_the_same_committed_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worktree = _archived_lane(tmp_path, monkeypatch).worktree
    archived_head = current_tracked_head(worktree)
    arguments = _start_change_arguments(worktree, archived_head)

    started = run_ethos(*arguments, cwd=worktree)
    recognized = run_ethos(*arguments, cwd=worktree)

    assert started["state"] == "started"
    assert recognized["state"] == "recognized"
    assert started["data"]["attestation"] == recognized["data"]["attestation"]
    assert os.environ["ETHOS_ACTOR"] == "agent:test:case:agent-test"


@pytest.mark.parametrize(
    ("later_path", "expected_state"),
    [("tests/later.txt", "recovered"), ("src/later.py", "blocked")],
)
def test_start_change_recovery_requires_later_commits_to_remain_in_scope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    later_path: str,
    expected_state: str,
) -> None:
    lifecycle = _archived_lane(tmp_path, monkeypatch)
    worktree = lifecycle.worktree
    archived_head = current_tracked_head(worktree)
    commit = rollover.commit_git_worktree
    advance = rollover.advance_committed_lease
    monkeypatch.setattr(
        rollover,
        "commit_git_worktree",
        lambda root, *, previous, message: (
            previous
            and {
                "verdict": (
                    "pass"
                    if git(root, "-c", "core.hooksPath=/dev/null", "commit", "-m", message)
                    is not None
                    else "block"
                ),
                "error": "",
            }
        ),
    )
    monkeypatch.setattr(
        rollover,
        "advance_committed_lease",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("interrupted")),
    )
    interrupted = start_change(
        root=worktree,
        change="hosted-verification-fix",
        intent="Repair hosted verification.",
        scope=("tests/**",),
        expect_head=archived_head,
        apply=True,
    )
    assert interrupted["state"] == "repair_required"
    assert leases_by_branch(worktree)[lifecycle.branch]["expected_head"] == archived_head

    later = worktree / later_path
    later.parent.mkdir(exist_ok=True)
    later.write_text("later in-scope work\n", encoding="utf-8")
    git(worktree, "add", later.relative_to(worktree).as_posix())
    git(
        worktree,
        "-c",
        "core.hooksPath=/dev/null",
        "commit",
        "-m",
        "test: continue started change",
    )
    monkeypatch.setattr(rollover, "commit_git_worktree", commit)
    monkeypatch.setattr(rollover, "advance_committed_lease", advance)

    recovered = start_change(
        root=worktree,
        change="hosted-verification-fix",
        intent="Repair hosted verification.",
        scope=("tests/**",),
        expect_head=archived_head,
        apply=True,
    )

    assert recovered["state"] == expected_state
    lease_head = leases_by_branch(worktree)[lifecycle.branch]["expected_head"]
    if expected_state == "recovered":
        assert recovered["head"] == current_tracked_head(worktree)
        assert lease_head == recovered["head"]
    else:
        assert lease_head == archived_head


def test_start_change_rejects_request_drift_for_an_existing_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worktree = _archived_lane(tmp_path, monkeypatch).worktree
    archived_head = current_tracked_head(worktree)
    started = run_ethos(*_start_change_arguments(worktree, archived_head), cwd=worktree)

    drifted = start_change(
        root=worktree,
        change="hosted-verification-fix",
        intent="A different intent must not reuse the committed generation.",
        scope=("tests/**",),
        expect_head=archived_head,
        apply=True,
    )

    assert started["state"] == "started"
    assert drifted["verdict"] == "block"
    assert drifted["required_gaps"] == ["openspec_change_request_mismatch"]


def test_start_change_does_not_recognize_a_forged_selected_member(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worktree = _archived_lane(tmp_path, monkeypatch).worktree
    archived_head = current_tracked_head(worktree)
    arguments = _start_change_arguments(worktree, archived_head)

    def commit_without_product_hooks(
        root: Path,
        *,
        previous: str,
        message: str,
        **_kwargs: object,
    ) -> dict[str, object]:
        assert current_tracked_head(root) == previous
        git(root, "commit", "-m", message)
        return {"verdict": "pass", "error": ""}

    monkeypatch.setattr(rollover, "commit_git_worktree", commit_without_product_hooks)
    started = run_ethos(*arguments, cwd=worktree)
    assert started["state"] == "started"
    _root, selected = read_attestation_set(worktree)
    valid = next(item for item in selected if item.predicate == "effect:openspec-change-start")
    payload = valid.model_dump(mode="python", exclude={"id"}) | {"verifier": "agent:forged"}
    forged = Attestation.issue(payload)
    git(worktree, "update-ref", "-d", ATTESTATION_SET_REF)
    record_attestations(worktree, (forged,))

    repeated = run_ethos_blocked(*arguments, cwd=worktree)

    assert repeated["state"] == "blocked"


def _start_change_arguments(
    worktree: Path,
    head: str,
    *extra: str,
    scope: str = "tests/**",
) -> tuple[str, ...]:
    return (
        "lane",
        "start-change",
        "hosted-verification-fix",
        "--intent",
        "Repair hosted verification.",
        "--scope",
        scope,
        "--expect-head",
        head,
        "--root",
        worktree.as_posix(),
        "--apply",
        "--json",
        *extra,
    )
