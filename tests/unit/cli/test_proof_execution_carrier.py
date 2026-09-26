"""Prove committed intent without rewriting a staged official archive."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from typing import Any

import pytest

import ethos.adapters.mutation.lane_lifecycle.archive.command as archive_command
import ethos.adapters.mutation.lane_lifecycle.archive.effect as archive_effect
import ethos.adapters.repo.proof_execution_carrier as execution_carrier
import ethos.surface.cli.root.proof as proof_cli
from ethos.adapters.mutation.proof import proof_gaps
from ethos.adapters.repo.proof_execution_carrier import ProofExecutionCarrier
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.store.state.lease.lifecycle.transitions import apply_lease_operation
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.coordination import LeaseOperationRequest
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.openspec_lifecycle import completed_lifecycle
from tests.support.proof import declare_native_proof_checks

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.plan import TransitionPlan


def _authoring_snapshot(root: Path) -> tuple[str, str, str]:
    """Retain both staged and unstaged bytes in test observations."""
    return (
        git(root, "diff", "--cached", "--binary"),
        git(root, "diff", "--binary"),
        git(root, "status", "--porcelain=v1"),
    )


def _staged_archive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, test_program: str
) -> tuple[Path, str, tuple[str, str, str]]:
    """Create committed intent and an untouched staged official archive."""
    lifecycle = completed_lifecycle(tmp_path, monkeypatch)
    authoring = lifecycle.worktree
    declare_native_proof_checks(authoring, test=test_program, typecheck="print('static green')")
    commit_fixture(authoring, "declare current proof gates")
    head = git(authoring, "rev-parse", "HEAD")
    lifecycle.stage_official_archive()
    git(authoring, "add", "--all")
    return authoring, head, _authoring_snapshot(authoring)


def _prove(authoring: Path, head: str, carrier: Path) -> dict[str, Any]:
    """Exercise public proof with original authority and a chosen executor."""
    completed = run_ethos_raw(
        "prove",
        "--change",
        "fixture-change",
        "--full",
        "--execute",
        "--expect-head",
        head,
        "--execution-root",
        str(carrier),
        "--json",
        cwd=authoring,
    )
    report = json.loads(completed.stdout)
    assert (completed.returncode == 0) is (report["verdict"] == "pass"), completed.stderr
    return report


def test_staged_archive_can_reprove_its_head_from_clean_carrier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep the original Lease and archive bytes while executing real current gates."""
    authoring, head, before = _staged_archive(
        tmp_path,
        monkeypatch,
        test_program=(
            "import subprocess; "
            "assert subprocess.run(['git', 'symbolic-ref', '-q', 'HEAD'], "
            "check=False, capture_output=True).returncode == 1"
        ),
    )
    carrier = tmp_path / "clean-carrier"
    git(authoring, "worktree", "add", "--detach", str(carrier), head)
    assert git(carrier, "rev-parse", "HEAD") == head
    assert git(carrier, "branch", "--show-current") == ""
    assert git(carrier, "status", "--porcelain=v1") == ""

    blocked = run_ethos_raw(
        "prove",
        "--change",
        "fixture-change",
        "--full",
        "--execute",
        "--expect-head",
        head,
        "--json",
        cwd=authoring,
    )
    assert blocked.returncode != 0
    assert json.loads(blocked.stdout)["verdict"] != "pass"
    assert before == _authoring_snapshot(authoring)

    report = _prove(authoring, head, carrier)
    assert report["verdict"] == "pass", report
    assert report["data"]["attestation"]["subject"] == f"git:commit:{head}"
    assert {check["action_id"] for check in report["data"]["checks"]} == {
        "sample-tests",
        "sample-static",
    }
    assert proof_gaps(authoring, head, change_id="fixture-change") == []
    assert before == _authoring_snapshot(authoring)


def test_fresh_carrier_proof_admits_native_staged_archive_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The original lane can consume new proof without rebuilding archive bytes."""
    authoring, head, before = _staged_archive(
        tmp_path, monkeypatch, test_program="print('current gate passed')"
    )
    carrier = tmp_path / "execution-carrier"
    git(authoring, "worktree", "add", "--detach", str(carrier), head)
    assert _prove(authoring, head, carrier)["verdict"] == "pass"

    monkeypatch.setattr(archive_command, "proof_gaps", proof_gaps)
    monkeypatch.setattr(archive_effect, "proof_gaps", proof_gaps)
    ready = archive_command.archive_change(
        root=authoring, change="fixture-change", expect_head=head
    )
    assert ready["state"] == "ready_to_finalize_archive", ready
    assert before == _authoring_snapshot(authoring)

    applied = archive_command.archive_change(
        root=authoring, change="fixture-change", expect_head=head, apply=True
    )
    assert applied["state"] == "repair_required", applied
    assert applied["required_gaps"] == ["proof_not_proven"]
    archived_head = git(authoring, "rev-parse", "HEAD")
    assert archived_head != head
    assert not (authoring / "openspec/changes/fixture-change").exists()
    assert git(authoring, "status", "--porcelain=v1") == ""

    post_proof = run_ethos_raw(
        "prove",
        "--change",
        "fixture-change",
        "--full",
        "--execute",
        "--expect-head",
        archived_head,
        "--json",
        cwd=authoring,
    )
    assert post_proof.returncode == 0, post_proof.stdout
    recovered = archive_command.archive_change(
        root=authoring, change="fixture-change", expect_head=head, apply=True
    )
    assert recovered["verdict"] == "pass", recovered


@pytest.mark.parametrize(
    ("condition", "expected_gap"),
    [
        ("foreign", "proof_execution_carrier_foreign"),
        ("attached", "proof_execution_carrier_attached"),
        ("wrong-head", "proof_execution_carrier_head_mismatch"),
        ("dirty", "proof_execution_carrier_dirty"),
    ],
)
def test_invalid_carrier_never_runs_checks_or_changes_staged_archive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    condition: str,
    expected_gap: str,
) -> None:
    """Reject independent carrier defects before spending a gate or signing proof."""
    authoring, head, before = _staged_archive(
        tmp_path, monkeypatch, test_program="raise SystemExit(75)"
    )
    carrier = tmp_path / "execution-carrier"
    if condition == "foreign":
        init_git_repo(carrier)
    elif condition == "attached":
        git(authoring, "worktree", "add", "-b", "carrier-branch", str(carrier), head)
    else:
        target = head if condition == "dirty" else git(authoring, "rev-parse", "HEAD^")
        git(authoring, "worktree", "add", "--detach", str(carrier), target)
        if condition == "dirty":
            (carrier / "untracked.txt").write_text("not committed\n", encoding="utf-8")
    report = _prove(authoring, head, carrier)
    assert report["required_gaps"] == [expected_gap], report
    assert report["data"] == {}
    assert before == _authoring_snapshot(authoring)
    assert proof_gaps(authoring, head, change_id="fixture-change")


@pytest.mark.parametrize(
    ("changed_root", "expected_gap"),
    [
        ("authoring", "proof_authoring_content_changed"),
        ("execution", "proof_execution_carrier_dirty"),
    ],
)
def test_source_drift_during_real_gate_retains_checks_but_signs_no_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    changed_root: str,
    expected_gap: str,
) -> None:
    """A passing check cannot promote its own source mutation into proof."""
    program = (
        "import os; from pathlib import Path; "
        "Path(os.environ['PROOF_DRIFT_TARGET']).write_text('drift\\n')"
    )
    authoring, head, before = _staged_archive(tmp_path, monkeypatch, test_program=program)
    carrier = tmp_path / "execution-carrier"
    git(authoring, "worktree", "add", "--detach", str(carrier), head)
    target = authoring / "README.md" if changed_root == "authoring" else carrier / "untracked.txt"
    monkeypatch.setenv("PROOF_DRIFT_TARGET", str(target))
    report = _prove(authoring, head, carrier)
    assert report["required_gaps"] == [expected_gap], report
    assert report["data"]["proof_attestation_selected"] is False
    assert report["data"]["artifact_reference"]["sha256"].startswith("sha256:")
    assert before[0] == _authoring_snapshot(authoring)[0]
    assert proof_gaps(authoring, head, change_id="fixture-change")


def test_lease_transfer_after_checks_retains_diagnostics_and_signs_no_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A fresh Lease owner, not completed checks, controls proof issuance."""
    authoring, head, before = _staged_archive(
        tmp_path, monkeypatch, test_program="print('current gate passed')"
    )
    carrier = tmp_path / "execution-carrier"
    git(authoring, "worktree", "add", "--detach", str(carrier), head)
    native = proof_cli.run_plan_checks

    def transfer_after_checks(
        *,
        repo: Path,
        plan: TransitionPlan,
        execute: bool,
        capacity: int | None = None,
        carrier: ProofExecutionCarrier | None = None,
    ) -> tuple[list[dict[str, object]], bool]:
        checks, passed = native(
            repo=repo, plan=plan, execute=execute, capacity=capacity, carrier=carrier
        )
        branch = git(authoring, "branch", "--show-current")
        lease = leases_by_branch(authoring)[branch]
        generation = lease["generation"]
        assert isinstance(generation, int)
        apply_lease_operation(
            state_database(authoring),
            request=LeaseOperationRequest(
                operation="transfer",
                branch=branch,
                holder_ref=str(lease["holder_ref"]),
                generation=generation,
                expires_at=str(lease["expires_at"]),
                target_holder_ref="agent:test:case:other",
                apply=True,
            ),
        )
        return checks, passed

    monkeypatch.setattr(proof_cli, "run_plan_checks", transfer_after_checks)
    report = _prove(authoring, head, carrier)
    assert report["required_gaps"] == ["proof_lease_generation_stale"], report
    assert report["data"]["proof_attestation_selected"] is False
    assert report["data"]["artifact_reference"]["sha256"].startswith("sha256:")
    assert before == _authoring_snapshot(authoring)
    assert proof_gaps(authoring, head, change_id="fixture-change")


def test_index_only_authoring_drift_is_not_hidden_by_unchanged_working_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A new staged blob changes the authoring effect even if its file stays put."""
    authoring, head, _before = _staged_archive(
        tmp_path, monkeypatch, test_program="print('current gate passed')"
    )
    carrier = tmp_path / "execution-carrier"
    git(authoring, "worktree", "add", "--detach", str(carrier), head)
    branch = git(authoring, "branch", "--show-current")
    guard = ProofExecutionCarrier.capture(
        authoring,
        carrier,
        head=head,
        tree=git(authoring, "rev-parse", "HEAD^{tree}"),
        lease=leases_by_branch(authoring)[branch],
    )
    archive_before = git(authoring, "diff", "--cached", "--binary", "--", "openspec")
    working_before = (authoring / "README.md").read_bytes()
    blob = tmp_path / "index-blob"
    blob.write_text("index only\n", encoding="utf-8")
    object_id = git(authoring, "hash-object", "-w", str(blob))
    git(authoring, "update-index", "--cacheinfo", f"100644,{object_id},README.md")

    assert (authoring / "README.md").read_bytes() == working_before
    assert git(authoring, "diff", "--cached", "--binary", "--", "openspec") == archive_before
    with pytest.raises(ValueError, match=r"^proof_authoring_content_changed$"):
        guard.recheck()


def test_authoring_ref_move_invalidates_captured_carrier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The original lane's HEAD, not only the carrier commit, remains bound."""
    authoring, head, _before = _staged_archive(
        tmp_path, monkeypatch, test_program="print('current gate passed')"
    )
    carrier = tmp_path / "execution-carrier"
    git(authoring, "worktree", "add", "--detach", str(carrier), head)
    branch = git(authoring, "branch", "--show-current")
    guard = ProofExecutionCarrier.capture(
        authoring,
        carrier,
        head=head,
        tree=git(authoring, "rev-parse", "HEAD^{tree}"),
        lease=leases_by_branch(authoring)[branch],
    )
    git(authoring, "update-ref", f"refs/heads/{branch}", f"{head}^", head)

    with pytest.raises(ValueError, match=r"^proof_authoring_source_changed$"):
        guard.recheck()


@pytest.mark.parametrize(
    ("defect", "expected"),
    [
        ("toplevel", "proof_execution_carrier_unregistered"),
        ("unavailable", "proof_execution_carrier_observation_unavailable"),
    ],
)
def test_carrier_recheck_rejects_untrusted_git_observation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str, expected: str
) -> None:
    """A matching HEAD cannot substitute for a registered, observable executor."""
    authoring, head, before = _staged_archive(
        tmp_path, monkeypatch, test_program="print('current gate passed')"
    )
    carrier = tmp_path / "execution-carrier"
    git(authoring, "worktree", "add", "--detach", str(carrier), head)
    branch = git(authoring, "branch", "--show-current")
    guard = ProofExecutionCarrier.capture(
        authoring,
        carrier,
        head=head,
        tree=git(authoring, "rev-parse", "HEAD^{tree}"),
        lease=leases_by_branch(authoring)[branch],
    )
    if defect == "toplevel":
        monkeypatch.setattr(execution_carrier, "git_stdout", lambda *_args: str(tmp_path))
    else:

        def unavailable(_root: Path) -> str:
            message = "git observation unavailable"
            raise OSError(message)

        monkeypatch.setattr(execution_carrier, "git_common_dir", unavailable)
    with pytest.raises(ValueError, match=rf"^{expected}$"):
        guard.recheck()
    assert before == _authoring_snapshot(authoring)


def test_execution_root_requires_exact_full_repository_proof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A partial or unspecified request cannot borrow carrier authority."""
    authoring, head, before = _staged_archive(
        tmp_path, monkeypatch, test_program="raise SystemExit(75)"
    )
    carrier = tmp_path / "execution-carrier"
    git(authoring, "worktree", "add", "--detach", str(carrier), head)
    completed = run_ethos_raw(
        "prove",
        "--change",
        "fixture-change",
        "--execute",
        "--execution-root",
        str(carrier),
        "--json",
        cwd=authoring,
    )
    assert completed.returncode != 0
    report = json.loads(completed.stdout)
    assert report["required_gaps"] == ["proof_execution_carrier_requires_full_exact_head"]
    assert before == _authoring_snapshot(authoring)
    assert proof_gaps(authoring, head, change_id="fixture-change")


def test_stale_expected_head_blocks_before_carrier_checks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Do not spend or accept gates for a caller's stale exact-head coordinate."""
    authoring, head, before = _staged_archive(
        tmp_path, monkeypatch, test_program="raise SystemExit(75)"
    )
    carrier = tmp_path / "execution-carrier"
    git(authoring, "worktree", "add", "--detach", str(carrier), head)
    stale = git(authoring, "rev-parse", "HEAD^")
    completed = run_ethos_raw(
        "prove",
        "--change",
        "fixture-change",
        "--full",
        "--execute",
        "--expect-head",
        stale,
        "--execution-root",
        str(carrier),
        "--json",
        cwd=authoring,
    )
    assert completed.returncode != 0
    report = json.loads(completed.stdout)
    assert report["required_gaps"] == ["expected_head_mismatch"], report
    assert report["data"] == {}
    assert before == _authoring_snapshot(authoring)
