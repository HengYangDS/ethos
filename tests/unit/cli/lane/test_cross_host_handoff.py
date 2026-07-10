from __future__ import annotations

import json
import subprocess
from pathlib import Path

from ethos.adapters.mutation.lane_lifecycle.handoff import core as handoff
from ethos.adapters.mutation.lanes import start_work_lane
from ethos.adapters.store.state.lease.projection import active_leases
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.lane_helpers import add_candidate_worktree
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo

HOLDER_A = "agent:test:case:source"
HOLDER_B = "agent:test:case:destination"


def _source_lane(tmp_path: Path) -> tuple[Path, Path, dict[str, object]]:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    started = start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        holder_ref=HOLDER_A,
        claim_id="sample-claim",
        apply=True,
    )
    assert started["ok"] is True
    return repo, worktree, started


def test_cross_host_export_is_content_addressed_and_excludes_sqlite_lease(tmp_path: Path) -> None:
    _, worktree, started = _source_lane(tmp_path)
    context = tmp_path / "handoff-context.md"
    context.write_text("Continue from the verified lane head.\n", encoding="utf-8")
    head = git(worktree, "rev-parse", "HEAD")
    lease = started["lease"]
    assert isinstance(lease, dict)
    output_root = tmp_path / "handoff-output"

    payload = run_ethos(
        "lane",
        "handoff",
        "export",
        "--branch",
        "work/feature",
        "--holder-ref",
        HOLDER_A,
        "--target-holder-ref",
        HOLDER_B,
        "--lease-id",
        str(lease["lease_id"]),
        "--epoch",
        str(lease["epoch"]),
        "--expect-head",
        head,
        "--context-file",
        context.as_posix(),
        "--output-root",
        output_root.as_posix(),
        "--apply",
        "--root",
        worktree.as_posix(),
        "--json",
        cwd=worktree,
    )

    assert payload["ok"] is True
    package_dir = output_root / payload["data"]["package_id"]
    manifest = json.loads((package_dir / "manifest.json").read_text(encoding="utf-8"))
    assert (package_dir / "repository.bundle").is_file()
    assert manifest["source_head"] == head
    assert manifest["target_holder_ref"] == HOLDER_B
    assert manifest["dirty_disposition"] == "clean"
    assert manifest["transfers_source_lease"] is False
    assert manifest["destination_creates_local_incarnation"] is True
    assert manifest["source_lease_binding"]["lease_id"] == lease["lease_id"]
    assert not any("sqlite" in path.name for path in package_dir.rglob("*"))
    assert "complete history" in git(
        worktree, "bundle", "verify", (package_dir / "repository.bundle").as_posix()
    )


def test_cross_host_export_blocks_dirty_lane_without_explicit_preservation(tmp_path: Path) -> None:
    _, worktree, started = _source_lane(tmp_path)
    (worktree / "README.md").write_text("# changed\n", encoding="utf-8")
    lease = started["lease"]
    assert isinstance(lease, dict)

    payload = run_ethos_blocked(
        "lane",
        "handoff",
        "export",
        "--branch",
        "work/feature",
        "--holder-ref",
        HOLDER_A,
        "--target-holder-ref",
        HOLDER_B,
        "--lease-id",
        str(lease["lease_id"]),
        "--epoch",
        str(lease["epoch"]),
        "--expect-head",
        git(worktree, "rev-parse", "HEAD"),
        "--context-text",
        "preserve work",
        "--output-root",
        (tmp_path / "handoff-output").as_posix(),
        "--apply",
        "--root",
        worktree.as_posix(),
        "--json",
        cwd=worktree,
    )

    assert "dirty_disposition_required" in payload["required_gaps"]


def test_cross_host_export_rejects_committed_disposition_when_lane_is_dirty(
    tmp_path: Path,
) -> None:
    _, worktree, started = _source_lane(tmp_path)
    (worktree / "README.md").write_text("# changed\n", encoding="utf-8")
    lease = started["lease"]
    assert isinstance(lease, dict)

    payload = run_ethos_blocked(
        "lane",
        "handoff",
        "export",
        "--branch",
        "work/feature",
        "--holder-ref",
        HOLDER_A,
        "--target-holder-ref",
        HOLDER_B,
        "--lease-id",
        str(lease["lease_id"]),
        "--epoch",
        str(lease["epoch"]),
        "--expect-head",
        git(worktree, "rev-parse", "HEAD"),
        "--context-text",
        "preserve work",
        "--dirty-disposition",
        "committed",
        "--output-root",
        (tmp_path / "handoff-output").as_posix(),
        "--apply",
        "--root",
        worktree.as_posix(),
        "--json",
        cwd=worktree,
    )

    assert "dirty_disposition_mismatch" in payload["required_gaps"]


def test_cross_host_import_creates_destination_local_incarnation_and_ack(tmp_path: Path) -> None:
    _, worktree, started = _source_lane(tmp_path)
    lease = started["lease"]
    assert isinstance(lease, dict)
    output_root = tmp_path / "handoff-output"
    exported = run_ethos(
        "lane",
        "handoff",
        "export",
        "--branch",
        "work/feature",
        "--holder-ref",
        HOLDER_A,
        "--target-holder-ref",
        HOLDER_B,
        "--lease-id",
        str(lease["lease_id"]),
        "--epoch",
        str(lease["epoch"]),
        "--expect-head",
        git(worktree, "rev-parse", "HEAD"),
        "--context-text",
        "destination context",
        "--output-root",
        output_root.as_posix(),
        "--apply",
        "--root",
        worktree.as_posix(),
        "--json",
        cwd=worktree,
    )
    package_dir = output_root / exported["data"]["package_id"]

    destination = init_repo(tmp_path / "destination")
    imported = run_ethos(
        "lane",
        "handoff",
        "import",
        "--package",
        package_dir.as_posix(),
        "--target-holder-ref",
        HOLDER_B,
        "--apply",
        "--root",
        destination.as_posix(),
        "--json",
        cwd=destination,
    )

    assert imported["ok"] is True
    assert imported["data"]["lease"]["holder_ref"] == HOLDER_B
    assert imported["data"]["lease"]["lease_id"] != lease["lease_id"]
    assert imported["data"]["lease"]["lane_incarnation_id"] != lease["lane_incarnation_id"]
    acknowledgement = imported["data"]["acknowledgement"]
    assert acknowledgement["package_id"] == exported["data"]["package_id"]
    assert acknowledgement["destination_head"] == git(worktree, "rev-parse", "HEAD")
    assert acknowledgement["source_lease_transferred"] is False

    acknowledgement_path = package_dir / "acknowledgement.json"
    acknowledgement_path.write_text(
        json.dumps(acknowledgement, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    revoked = run_ethos(
        "lane",
        "handoff",
        "revoke-source",
        "--package",
        package_dir.as_posix(),
        "--acknowledgement",
        acknowledgement_path.as_posix(),
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
    assert revoked["data"]["receipt"]["operation"] == "cross-host-source-revoke"
    assert active_leases(worktree.parent / "repo" / ".ethos" / "state" / "state.sqlite") == []


def test_cross_host_import_restores_preserved_tracked_and_untracked_work(tmp_path: Path) -> None:
    _, worktree, started = _source_lane(tmp_path)
    lease = started["lease"]
    assert isinstance(lease, dict)
    (worktree / "README.md").write_text("# preserved tracked\n", encoding="utf-8")
    (worktree / "notes.txt").write_text("preserved untracked\n", encoding="utf-8")
    output_root = tmp_path / "handoff-output"
    exported = run_ethos(
        "lane",
        "handoff",
        "export",
        "--branch",
        "work/feature",
        "--holder-ref",
        HOLDER_A,
        "--target-holder-ref",
        HOLDER_B,
        "--lease-id",
        str(lease["lease_id"]),
        "--epoch",
        str(lease["epoch"]),
        "--expect-head",
        git(worktree, "rev-parse", "HEAD"),
        "--context-text",
        "preserved destination context",
        "--dirty-disposition",
        "preserved",
        "--output-root",
        output_root.as_posix(),
        "--apply",
        "--root",
        worktree.as_posix(),
        "--json",
        cwd=worktree,
    )
    package_dir = output_root / exported["data"]["package_id"]
    destination = init_repo(tmp_path / "destination")

    imported = run_ethos(
        "lane",
        "handoff",
        "import",
        "--package",
        package_dir.as_posix(),
        "--target-holder-ref",
        HOLDER_B,
        "--apply",
        "--root",
        destination.as_posix(),
        "--json",
        cwd=destination,
    )

    imported_worktree = Path(imported["data"]["worktree"]["path"])
    assert (imported_worktree / "README.md").read_text(encoding="utf-8") == "# preserved tracked\n"
    assert (imported_worktree / "notes.txt").read_text(encoding="utf-8") == (
        "preserved untracked\n"
    )


def test_preserved_dirty_content_changes_package_identity(tmp_path: Path) -> None:
    _, worktree, started = _source_lane(tmp_path)
    lease = started["lease"]
    assert isinstance(lease, dict)
    output_root = tmp_path / "handoff-output"

    (worktree / "README.md").write_text("# first\n", encoding="utf-8")
    first = run_ethos(
        "lane",
        "handoff",
        "export",
        "--branch",
        "work/feature",
        "--holder-ref",
        HOLDER_A,
        "--target-holder-ref",
        HOLDER_B,
        "--lease-id",
        str(lease["lease_id"]),
        "--epoch",
        str(lease["epoch"]),
        "--expect-head",
        git(worktree, "rev-parse", "HEAD"),
        "--context-text",
        "preserved context",
        "--dirty-disposition",
        "preserved",
        "--output-root",
        output_root.as_posix(),
        "--apply",
        "--root",
        worktree.as_posix(),
        "--json",
        cwd=worktree,
    )
    (worktree / "README.md").write_text("# second\n", encoding="utf-8")
    second = run_ethos(
        "lane",
        "handoff",
        "export",
        "--branch",
        "work/feature",
        "--holder-ref",
        HOLDER_A,
        "--target-holder-ref",
        HOLDER_B,
        "--lease-id",
        str(lease["lease_id"]),
        "--epoch",
        str(lease["epoch"]),
        "--expect-head",
        git(worktree, "rev-parse", "HEAD"),
        "--context-text",
        "preserved context",
        "--dirty-disposition",
        "preserved",
        "--output-root",
        output_root.as_posix(),
        "--apply",
        "--root",
        worktree.as_posix(),
        "--json",
        cwd=worktree,
    )

    assert first["data"]["package_id"] != second["data"]["package_id"]


def test_cross_host_import_rolls_back_git_state_when_lease_creation_fails(
    tmp_path: Path, monkeypatch
) -> None:
    _, worktree, started = _source_lane(tmp_path)
    lease = started["lease"]
    assert isinstance(lease, dict)
    output_root = tmp_path / "handoff-output"
    exported = run_ethos(
        "lane",
        "handoff",
        "export",
        "--branch",
        "work/feature",
        "--holder-ref",
        HOLDER_A,
        "--target-holder-ref",
        HOLDER_B,
        "--lease-id",
        str(lease["lease_id"]),
        "--epoch",
        str(lease["epoch"]),
        "--expect-head",
        git(worktree, "rev-parse", "HEAD"),
        "--context-text",
        "destination context",
        "--output-root",
        output_root.as_posix(),
        "--apply",
        "--root",
        worktree.as_posix(),
        "--json",
        cwd=worktree,
    )
    package_dir = output_root / exported["data"]["package_id"]
    destination = init_repo(tmp_path / "destination")
    expected_worktree = destination.with_name("destination-work-feature")

    def fail_acquire(*args, **kwargs):  # noqa: ARG001, RUF100 - test double preserves the patched callable signature
        raise ValueError("simulated_lease_failure")  # noqa: EM101, RUF100 - machine-readable gap token is the exception contract

    monkeypatch.setattr(handoff.handoff_package, "acquire_lease", fail_acquire)

    payload = handoff.import_cross_host_handoff(
        root=destination,
        package=package_dir,
        target_holder_ref=HOLDER_B,
        apply=True,
    )

    assert payload["ok"] is False
    assert not expected_worktree.exists()
    assert (
        subprocess.run(
            ["git", "show-ref", "--verify", "refs/heads/work/feature"],
            cwd=destination,
            check=False,
        ).returncode
        != 0
    )
