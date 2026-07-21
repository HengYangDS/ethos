from __future__ import annotations

import errno
import json
import os
import sqlite3
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from ethos.adapters.mutation.lane_lifecycle.handoff import core as handoff
from ethos.adapters.mutation.lanes import start_work_lane
from ethos.adapters.store.state.lease.lifecycle.core import advance_lease_head
from ethos.adapters.store.state.lease.lifecycle.core import renew_lease
from ethos.adapters.store.state.lease.projection import active_leases
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.lane_helpers import add_candidate_worktree
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo

HOLDER_A = "agent:test:case:source"
HOLDER_B = "agent:test:case:destination"


@pytest.fixture(autouse=True)
def _source_actor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ETHOS_ACTOR", HOLDER_A)


def _lease(started: dict[str, object]) -> dict[str, object]:
    return cast("dict[str, object]", started["lease"])


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


def _export(
    worktree: Path,
    started: dict[str, object],
    *,
    output_root: Path,
    context: str,
    context_option: str = "--context-text",
    dirty_disposition: str = "",
    expected_expires_at: str = "",
    expected_payload_sha256: str = "",
    blocked: bool = False,
) -> dict[str, object]:
    lease = _lease(started)
    source_args = (
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
        "--expires-at",
        expected_expires_at or str(lease["expires_at"]),
        "--payload-sha256",
        expected_payload_sha256 or str(lease["payload_sha256"]),
        "--expect-head",
        git(worktree, "rev-parse", "HEAD"),
    )
    args = (
        "lane",
        "handoff",
        "export",
        *source_args,
        context_option,
        context,
        *(("--dirty-disposition", dirty_disposition) if dirty_disposition else ()),
        "--output-root",
        output_root.as_posix(),
        "--apply",
        "--root",
        worktree.as_posix(),
        "--json",
    )
    runner = run_ethos_blocked if blocked else run_ethos
    return runner(*args, cwd=worktree)


def test_cross_host_export_rejects_stale_complete_generation(tmp_path: Path) -> None:
    _, worktree, started = _source_lane(tmp_path)
    for field, value in (
        ("expected_expires_at", "2000-01-01T00:00:00+00:00"),
        ("expected_payload_sha256", "0" * 64),
    ):
        payload = _export(
            worktree,
            started,
            output_root=tmp_path / "handoff-output",
            context="complete generation",
            blocked=True,
            **{field: value},
        )

        assert "lease_generation_stale" in payload["required_gaps"]


@pytest.mark.parametrize(
    ("operation", "gap"),
    [("export", "lease_actor_mismatch"), ("import", "handoff_target_actor_mismatch")],
)
def test_cross_host_handoff_requires_bound_actor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str, gap: str
) -> None:
    _, worktree, started = _source_lane(tmp_path)
    if operation == "export":
        monkeypatch.setenv("ETHOS_ACTOR", HOLDER_B)
        payload = _export(
            worktree,
            started,
            output_root=tmp_path / "handoff-output",
            context="source actor",
            blocked=True,
        )
    else:
        exported = _export(
            worktree, started, output_root=tmp_path / "handoff-output", context="target actor"
        )
        monkeypatch.setenv("ETHOS_ACTOR", HOLDER_A)
        payload = _import(
            tmp_path / "handoff-output" / exported["data"]["package_id"],
            init_repo(tmp_path / "destination"),
            blocked=True,
        )
    assert gap in payload["required_gaps"]


def _import(package: Path, destination: Path, *, blocked: bool = False) -> dict[str, object]:
    runner = run_ethos_blocked if blocked else run_ethos
    return runner(
        "lane",
        "handoff",
        "import",
        "--package",
        package.as_posix(),
        "--target-holder-ref",
        HOLDER_B,
        "--apply",
        "--root",
        destination.as_posix(),
        "--json",
        cwd=destination,
    )


def _handoff_args(
    worktree: Path,
    started: dict[str, object],
    package: Path,
    acknowledgement: Path,
) -> tuple[str, ...]:
    lease = _lease(started)
    return (
        "--package",
        package.as_posix(),
        "--acknowledgement",
        acknowledgement.as_posix(),
        "--holder-ref",
        HOLDER_A,
        "--lease-id",
        str(lease["lease_id"]),
        "--epoch",
        str(lease["epoch"]),
        "--expires-at",
        str(lease["expires_at"]),
        "--payload-sha256",
        str(lease["payload_sha256"]),
        "--expect-head",
        git(worktree, "rev-parse", "HEAD"),
    )


def _import_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, context: str
) -> tuple[Path, Path, dict[str, object], Path, Path]:
    repo, worktree, started = _source_lane(tmp_path)
    output_root = tmp_path / "handoff-output"
    exported = _export(worktree, started, output_root=output_root, context=context)
    monkeypatch.setenv("ETHOS_ACTOR", HOLDER_B)
    return (
        repo,
        worktree,
        started,
        output_root / str(exported["data"]["package_id"]),
        init_repo(tmp_path / "destination"),
    )


def _exported(tmp_path: Path, context: str) -> tuple[Path, dict[str, object], Path]:
    _, worktree, started = _source_lane(tmp_path)
    output_root = tmp_path / "handoff-output"
    exported = _export(worktree, started, output_root=output_root, context=context)
    return worktree, started, output_root / str(exported["data"]["package_id"])


def _acknowledgement_path(tmp_path: Path, acknowledgement: object) -> Path:
    path = tmp_path / "acknowledgement.json"
    path.write_text(json.dumps(acknowledgement, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _assert_no_import_carriers(destination: Path) -> None:
    assert not destination.with_name("destination-work-feature").exists()
    assert _git_exit(destination, "show-ref", "--verify", "refs/heads/work/feature") != 0


def _assert_no_temporary_handoff_refs(destination: Path) -> None:
    assert git(destination, "for-each-ref", "--format=%(refname)", "refs/ethos/handoff") == ""


def _git_exit(root: Path, *args: str) -> int:
    return subprocess.run(["git", *args], cwd=root, check=False).returncode


def _manifest(package: Path) -> dict[str, object]:
    return cast("dict[str, object]", json.loads((package / "manifest.json").read_text()))


def _apply_import(destination: Path, package: Path, manifest: dict[str, object]) -> None:
    handoff.handoff_package.apply_handoff_import(
        destination=destination,
        package=package,
        manifest=manifest,
        target_holder_ref=HOLDER_B,
    )


def _revoke_source(
    worktree: Path,
    started: dict[str, object],
    package: Path,
    acknowledgement: Path,
    *,
    blocked: bool = False,
) -> dict[str, object]:
    runner = run_ethos_blocked if blocked else run_ethos
    return runner(
        "lane",
        "handoff",
        "revoke-source",
        *_handoff_args(worktree, started, package, acknowledgement),
        "--apply",
        "--root",
        worktree.as_posix(),
        "--json",
        cwd=worktree,
    )


def test_cross_host_export_is_content_addressed_and_excludes_sqlite_lease(
    tmp_path: Path,
) -> None:
    _, worktree, started = _source_lane(tmp_path)
    context = tmp_path / "handoff-context.md"
    context.write_text("Continue from the verified lane head.\n", encoding="utf-8")
    head = git(worktree, "rev-parse", "HEAD")
    output_root = tmp_path / "handoff-output"
    payload = _export(
        worktree,
        started,
        output_root=output_root,
        context=context.as_posix(),
        context_option="--context-file",
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
    lease = _lease(started)
    assert manifest["source_lease_binding"]["lease_id"] == lease["lease_id"]
    assert manifest["source_lease_binding"]["expires_at"] == lease["expires_at"]
    assert manifest["source_lease_binding"]["payload_sha256"] == lease["payload_sha256"]
    assert not any("sqlite" in path.name for path in package_dir.rglob("*"))
    verification = subprocess.run(
        ["git", "bundle", "verify", (package_dir / "repository.bundle").as_posix()],
        cwd=worktree,
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "LANG": "C", "LC_ALL": "C"},
    )
    assert "complete history" in verification.stdout


def test_cross_host_package_identity_binds_exact_lease_generation(tmp_path: Path) -> None:
    repo, worktree, started = _source_lane(tmp_path)
    output_root = tmp_path / "handoff-output"
    first = _export(worktree, started, output_root=output_root, context="same content")
    lease = _lease(started)
    renewed = renew_lease(
        repo / ".ethos/state/state.sqlite",
        subject="work/feature",
        holder_ref=HOLDER_A,
        expected_lease_id=str(lease["lease_id"]),
        expected_epoch=int(lease["epoch"]),
        expected_head=git(worktree, "rev-parse", "HEAD"),
        expected_expires_at=str(lease["expires_at"]),
        expected_payload_sha256=str(lease["payload_sha256"]),
    )
    second = _export(
        worktree,
        {**started, "lease": renewed},
        output_root=output_root,
        context="same content",
    )

    assert first["data"]["package_id"] != second["data"]["package_id"]


@pytest.mark.parametrize("drift", ["head", "dirty", "lease"])
def test_cross_host_export_rejects_snapshot_drift_before_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    drift: str,
) -> None:
    repo, worktree, started = _source_lane(tmp_path)
    original = handoff.handoff_package.write_handoff_package

    def drift_then_write(**kwargs):
        if drift == "head":
            (worktree / "second.txt").write_text("second\n", encoding="utf-8")
            git(worktree, "add", "second.txt")
            git(worktree, "commit", "-m", "second")
        elif drift == "dirty":
            (worktree / "README.md").write_text("# drift\n", encoding="utf-8")
        else:
            lease = _lease(started)
            advance_lease_head(
                repo / ".ethos/state/state.sqlite",
                subject="work/feature",
                holder_ref=HOLDER_A,
                expected_lease_id=str(lease["lease_id"]),
                expected_epoch=int(lease["epoch"]),
                old_head=str(lease["expected_head"]),
                new_head=str(lease["expected_head"]),
                expected_expires_at=str(lease["expires_at"]),
                expected_payload_sha256=str(lease["payload_sha256"]),
            )
        return original(**kwargs)

    monkeypatch.setattr(handoff.handoff_package, "write_handoff_package", drift_then_write)

    payload = _export(
        worktree,
        started,
        output_root=tmp_path / "handoff-output",
        context="atomic snapshot",
        blocked=True,
    )

    assert payload["required_gaps"] == [f"handoff_export_failed:handoff_export_{drift}_drift"]
    assert not list((tmp_path / "handoff-output").glob("handoff:*"))


def test_cross_host_import_rejects_manifest_identity_tampering(tmp_path: Path) -> None:
    _, _, package_dir = _exported(tmp_path, "identity")
    manifest_path = package_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source_lease_binding"]["expires_at"] = "2099-01-01T00:00:00+00:00"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    payload = _import(package_dir, init_repo(tmp_path / "destination"), blocked=True)

    assert "handoff_package_id_mismatch" in payload["required_gaps"]


@pytest.mark.parametrize(
    ("duplicate_field", "gap"),
    [
        ("kind", "handoff_artifact_kind_duplicate:context"),
        ("path", "handoff_artifact_path_duplicate:context.md"),
    ],
)
def test_cross_host_import_rejects_duplicate_artifact_identity(
    tmp_path: Path,
    duplicate_field: str,
    gap: str,
) -> None:
    _, _, package_dir = _exported(tmp_path, "artifact identity")
    manifest_path = package_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    duplicate = dict(manifest["artifacts"][1])
    if duplicate_field == "path":
        duplicate["kind"] = "tracked_patch"
    manifest["artifacts"].append(duplicate)
    manifest["package_id"] = handoff.handoff_package._content_id(
        "handoff",
        {key: value for key, value in manifest.items() if key != "package_id"},
    )
    replacement = package_dir.with_name(manifest["package_id"])
    package_dir.rename(replacement)
    manifest_path = replacement / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    payload = _import(replacement, init_repo(tmp_path / "destination"), blocked=True)

    assert gap in payload["required_gaps"]


def test_cross_host_export_dirty_disposition_matrix(tmp_path: Path) -> None:
    for index, disposition, gap in (
        ("required", "", "dirty_disposition_required"),
        ("mismatch", "committed", "dirty_disposition_mismatch"),
    ):
        _, worktree, started = _source_lane(tmp_path / index)
        (worktree / "README.md").write_text("# changed\n", encoding="utf-8")
        payload = _export(
            worktree,
            started,
            output_root=tmp_path / index / "handoff-output",
            context="preserve work",
            dirty_disposition=disposition,
            blocked=True,
        )
        assert gap in payload["required_gaps"]


@pytest.mark.parametrize(
    ("mutation", "gap"),
    [
        ("", ""),
        ("id", "handoff_acknowledgement_id_mismatch"),
        ("tree", "handoff_acknowledgement_tree_mismatch"),
    ],
)
def test_cross_host_import_acknowledgement_and_source_revoke(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str, gap: str
) -> None:
    _, worktree, started, package_dir, destination = _import_input(
        tmp_path, monkeypatch, "destination context"
    )
    imported = _import(package_dir, destination)
    lease = _lease(started)

    assert imported["ok"] is True
    assert (
        imported["data"]["lease"]["holder_ref"],
        imported["data"]["lease"]["lease_id"] != lease["lease_id"],
        imported["data"]["lease"]["lane_incarnation_id"] != lease["lane_incarnation_id"],
    ) == (HOLDER_B, True, True)
    acknowledgement = imported["data"]["acknowledgement"]
    assert acknowledgement["package_id"] == package_dir.name
    imported_worktree = Path(imported["data"]["worktree"]["path"])
    assert (acknowledgement["destination_head"], acknowledgement["destination_tree"]) == (
        git(imported_worktree, "rev-parse", "HEAD"),
        git(imported_worktree, "rev-parse", "HEAD^{tree}"),
    )
    assert (
        acknowledgement["destination_holder_ref"],
        acknowledgement["destination_lease_id"],
        acknowledgement["destination_lease_epoch"],
    ) == (HOLDER_B, imported["data"]["lease"]["lease_id"], imported["data"]["lease"]["epoch"])
    assert (
        acknowledgement["destination_lease_expected_head"],
        acknowledgement["destination_lease_expires_at"],
        acknowledgement["destination_lease_payload_sha256"],
    ) == tuple(
        imported["data"]["lease"][key] for key in ("expected_head", "expires_at", "payload_sha256")
    )
    assert acknowledgement["acknowledgement_id"].startswith("handoff-ack:")
    assert acknowledgement["source_lease_transferred"] is False
    if mutation == "id":
        acknowledgement["destination_lease_epoch"] = (
            int(acknowledgement["destination_lease_epoch"]) + 1
        )
    elif mutation == "tree":
        acknowledgement["destination_tree"] = "f" * 40
        acknowledgement["acknowledgement_id"] = handoff.handoff_package._content_id(  # noqa: SLF001, RUF100 - adversarial receipt fixture
            "handoff-ack",
            {key: value for key, value in acknowledgement.items() if key != "acknowledgement_id"},
        )
    acknowledgement_path = _acknowledgement_path(tmp_path, acknowledgement)
    if mutation:
        monkeypatch.setenv("ETHOS_ACTOR", HOLDER_A)
        payload = _revoke_source(worktree, started, package_dir, acknowledgement_path, blocked=True)
        assert gap in payload["required_gaps"]
        assert active_leases(worktree.parent / "repo" / ".ethos" / "state" / "state.sqlite")
    else:
        monkeypatch.setenv("ETHOS_ACTOR", HOLDER_B)
        blocked = _revoke_source(worktree, started, package_dir, acknowledgement_path, blocked=True)
        assert "lease_actor_mismatch" in blocked["required_gaps"]
        monkeypatch.setenv("ETHOS_ACTOR", HOLDER_A)
        revoked = _revoke_source(worktree, started, package_dir, acknowledgement_path)
        assert revoked["data"]["receipt"]["operation"] == "cross-host-source-revoke"
        assert active_leases(worktree.parent / "repo" / ".ethos" / "state" / "state.sqlite") == []


def test_cross_host_import_restores_preserved_tracked_and_untracked_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, worktree, started = _source_lane(tmp_path)
    (worktree / "README.md").write_text("# preserved tracked\n", encoding="utf-8")
    (worktree / "notes.txt").write_text("preserved untracked\n", encoding="utf-8")
    output_root = tmp_path / "handoff-output"
    exported = _export(
        worktree,
        started,
        output_root=output_root,
        context="preserved destination context",
        dirty_disposition="preserved",
    )
    (worktree / "README.md").write_text("# second identity\n", encoding="utf-8")
    second = _export(
        worktree,
        started,
        output_root=output_root,
        context="preserved destination context",
        dirty_disposition="preserved",
    )
    assert exported["data"]["package_id"] != second["data"]["package_id"]
    package_dir = output_root / exported["data"]["package_id"]
    destination = init_repo(tmp_path / "destination")
    monkeypatch.setenv("ETHOS_ACTOR", HOLDER_B)

    imported = _import(package_dir, destination)

    imported_worktree = Path(imported["data"]["worktree"]["path"])
    assert (imported_worktree / "README.md").read_text(encoding="utf-8") == "# preserved tracked\n"
    assert (imported_worktree / "notes.txt").read_text(encoding="utf-8") == (
        "preserved untracked\n"
    )


def test_cross_host_import_rolls_back_git_state_when_lease_creation_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, _, _, package_dir, destination = _import_input(tmp_path, monkeypatch, "destination context")

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
    _assert_no_import_carriers(destination)


def test_cross_host_import_path_collision_leaves_no_attempt_ref(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, _, package_dir, destination = _import_input(tmp_path, monkeypatch, "path collision")
    destination.with_name("destination-work-feature").mkdir()

    payload = _import(package_dir, destination, blocked=True)

    assert "handoff_destination_path_exists" in payload["required_gaps"][0]
    assert _git_exit(destination, "show-ref", "--verify", "refs/heads/work/feature") != 0


def test_cross_host_import_unbundles_without_temporary_ref(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, _, _, package_dir, destination = _import_input(tmp_path, monkeypatch, "direct unbundle")
    original_run = subprocess.run
    commands: list[tuple[str, ...]] = []

    def reject_temporary_ref(args, *positional, **kwargs):
        command = tuple(map(str, args))
        assert not any("refs/ethos/handoff/" in argument for argument in command)
        commands.append(command)
        return original_run(args, *positional, **kwargs)

    monkeypatch.setattr(handoff.handoff_package.subprocess, "run", reject_temporary_ref)

    payload = _import(package_dir, destination)

    assert payload["ok"] is True
    assert any(command[1:3] == ("bundle", "list-heads") for command in commands)
    assert any(command[1:3] == ("bundle", "unbundle") for command in commands)


def test_cross_host_import_preserves_same_head_ref_created_during_cas_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, _, _, package_dir, destination = _import_input(tmp_path, monkeypatch, "ref race")
    manifest = _manifest(package_dir)
    head = str(manifest["source_head"])
    original_run = subprocess.run

    def create_ref_then_fail(args, *positional, cwd, **kwargs):
        if args[:3] == ("git", "update-ref", "refs/heads/work/feature"):
            original_run(
                ["git", "update-ref", "refs/heads/work/feature", head, "0" * 40],
                cwd=cwd,
                check=True,
                capture_output=True,
                text=True,
            )
            return subprocess.CompletedProcess(args, 1, "", "simulated_cas_race")
        return original_run(args, *positional, cwd=cwd, **kwargs)

    monkeypatch.setattr(handoff.handoff_package.subprocess, "run", create_ref_then_fail)

    with pytest.raises(subprocess.SubprocessError, match="simulated_cas_race"):
        _apply_import(destination, package_dir, manifest)

    assert git(destination, "rev-parse", "refs/heads/work/feature") == head


@pytest.mark.parametrize("field", ["source_head", "source_tree"])
def test_cross_host_import_rejects_manifest_drift_before_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    _, _, _, package_dir, destination = _import_input(tmp_path, monkeypatch, "bundle identity")
    manifest = cast("dict[str, object]", json.loads((package_dir / "manifest.json").read_text()))
    manifest[field] = "f" * 40

    with pytest.raises(ValueError, match="handoff_package_changed_after_verification"):
        _apply_import(destination, package_dir, manifest)

    _assert_no_import_carriers(destination)
    _assert_no_temporary_handoff_refs(destination)


@pytest.mark.parametrize("drift", ["heads", "bundle", "destination"])
def test_cross_host_import_cleans_carriers_after_identity_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, drift: str
) -> None:
    _, _, _, package_dir, destination = _import_input(tmp_path, monkeypatch, "bundle mismatch")
    manifest, original = _manifest(package_dir), handoff.handoff_package.run_git
    destination_worktree = destination.with_name("destination-work-feature")

    def mismatched_tree(root: Path, *args: str, **kwargs):
        result = original(root, *args, **kwargs)
        heads = drift == "heads" and args[:2] == ("bundle", "list-heads")
        bundle_tree = drift == "bundle" and args[0] == "rev-parse" and args[-1].endswith("^{tree}")
        worktree_tree = (
            drift == "destination"
            and root == destination_worktree
            and args
            == (
                "rev-parse",
                "HEAD^{tree}",
            )
        )
        output = "f" * 40 + (" refs/heads/other\n" if heads else "\n")
        return (
            subprocess.CompletedProcess(result.args, 0, output, "")
            if heads or bundle_tree or worktree_tree
            else result
        )

    monkeypatch.setattr(handoff.handoff_package, "run_git", mismatched_tree)

    expected = "bundle" if drift == "heads" else drift
    with pytest.raises(ValueError, match=f"handoff_{expected}.*identity.*(?:mismatch|drift)"):
        _apply_import(destination, package_dir, manifest)

    _assert_no_temporary_handoff_refs(destination)
    assert not destination_worktree.exists()


def test_cross_host_import_rejects_nonregular_snapshot_entry(tmp_path: Path) -> None:
    package = tmp_path / "package"
    package.mkdir()
    os.mkfifo(package / "pipe")
    destination = init_repo(tmp_path / "destination")
    manifest = {
        "package_id": "handoff:" + "a" * 64,
        "source_lane_ref": "work/feature",
        "source_head": "b" * 40,
        "source_tree": "c" * 40,
    }

    with pytest.raises(ValueError, match="handoff_artifact_unsafe:pipe"):
        handoff.handoff_package.apply_handoff_import(
            destination=destination,
            package=package,
            manifest=manifest,
            target_holder_ref=HOLDER_B,
        )


@pytest.mark.parametrize("error", [RuntimeError("runtime"), sqlite3.OperationalError("locked")])
def test_cross_host_import_compensates_non_value_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    _, _, _, package_dir, destination = _import_input(tmp_path, monkeypatch, "broad cleanup")
    monkeypatch.setattr(
        handoff.handoff_package,
        "acquire_lease",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(error),
    )

    with pytest.raises(type(error), match=str(error)):
        _apply_import(
            destination,
            package_dir,
            cast("dict[str, object]", json.loads((package_dir / "manifest.json").read_text())),
        )

    _assert_no_import_carriers(destination)


def test_cross_host_import_revokes_destination_lease_after_restore_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, _, _, package_dir, destination = _import_input(tmp_path, monkeypatch, "restore failure")
    monkeypatch.setattr(
        handoff.handoff_package,
        "_restore_preserved_work",
        lambda **_: (_ for _ in ()).throw(ValueError("simulated_restore_failure")),
    )

    payload = handoff.import_cross_host_handoff(
        root=destination,
        package=package_dir,
        target_holder_ref=HOLDER_B,
        apply=True,
    )

    assert payload["ok"] is False
    assert active_leases(destination / ".ethos" / "state" / "state.sqlite") == []


@pytest.mark.parametrize("race", ["renew", "revoke"])
def test_cross_host_import_rejects_lease_race_before_acknowledgement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    race: str,
) -> None:
    _, _, _, package_dir, destination = _import_input(tmp_path, monkeypatch, "lease race")
    commit_import = handoff.handoff_package._commit_import

    def race_then_commit(_destination, _worktree, _manifest, lease):
        db_path = destination / ".ethos/state/state.sqlite"
        arguments = {
            "subject": "work/feature",
            "holder_ref": HOLDER_B,
            "expected_lease_id": str(lease["lease_id"]),
            "expected_epoch": int(lease["epoch"]),
            "expected_head": str(lease["expected_head"]),
            "expected_expires_at": str(lease["expires_at"]),
            "expected_payload_sha256": str(lease["payload_sha256"]),
        }
        if race == "renew":
            renew_lease(db_path, **arguments)
        else:
            handoff.handoff_package.revoke_lease(db_path, **arguments)
        return commit_import(_destination, _worktree, _manifest, lease)

    monkeypatch.setattr(
        handoff.handoff_package,
        "_commit_import",
        race_then_commit,
    )

    payload = handoff.import_cross_host_handoff(
        root=destination, package=package_dir, target_holder_ref=HOLDER_B, apply=True
    )

    assert payload["ok"] is False
    assert payload["required_gaps"][0].startswith("handoff_import_failed:")
    assert any(
        token in payload["required_gaps"][0] for token in ("lease_", "work_lane_missing_lease")
    )
    assert not payload.get("data", {}).get("acknowledgement")


def test_cross_host_export_does_not_overwrite_existing_content_addressed_package(
    tmp_path: Path,
) -> None:
    worktree, started, package_dir = _exported(tmp_path, "immutable package")
    second = _export(worktree, started, output_root=package_dir.parent, context="immutable package")
    assert second["data"]["package_id"] == package_dir.name
    sentinel = package_dir / "sentinel"
    sentinel.write_text("preserve", encoding="utf-8")

    collision = _export(
        worktree,
        started,
        output_root=package_dir.parent,
        context="immutable package",
        blocked=True,
    )

    assert "handoff_package_collision_or_invalid" in collision["required_gaps"][0]
    assert sentinel.read_text(encoding="utf-8") == "preserve"


@pytest.mark.parametrize(
    ("content", "gap"),
    [
        (None, "handoff_acknowledgement_unreadable"),
        ("{", "handoff_acknowledgement_invalid_json"),
        ("[]", "handoff_acknowledgement_invalid"),
    ],
)
def test_cross_host_acknowledgement_reader_fails_closed(
    tmp_path: Path, content: str | None, gap: str
) -> None:
    acknowledgement = tmp_path / "acknowledgement.json"
    if content is not None:
        acknowledgement.write_text(content, encoding="utf-8")

    _, gaps = handoff.handoff_package.verified_handoff_acknowledgement(
        acknowledgement=acknowledgement,
        root=tmp_path,
    )

    assert gaps == [gap]


@pytest.mark.parametrize(
    ("errno_value", "mode"), [(errno.EEXIST, "concurrent"), (errno.EIO, "failure")]
)
def test_cross_host_export_publish_collision_matrix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, errno_value: int, mode: str
) -> None:
    worktree, started, package_dir = _exported(tmp_path, "concurrent package")
    if mode == "concurrent":
        original_exists = Path.exists

        def hide_once(path: Path) -> bool:
            if path == package_dir:
                monkeypatch.setattr(Path, "exists", original_exists)
                return False
            return original_exists(path)

        monkeypatch.setattr(Path, "exists", hide_once)
    monkeypatch.setattr(
        handoff.handoff_package.ctypes,
        "CDLL",
        lambda *_args, **_kwargs: SimpleNamespace(
            renameat2=lambda *_: -1,
            renamex_np=lambda *_: -1,
        ),
    )
    monkeypatch.setattr(handoff.handoff_package.ctypes, "get_errno", lambda: errno_value)
    payload = _export(
        worktree,
        started,
        output_root=tmp_path / "failed-publish" if mode == "failure" else package_dir.parent,
        context="concurrent package",
        blocked=mode == "failure",
    )
    if mode == "failure":
        assert payload["required_gaps"][0].startswith("handoff_export_failed:[Errno 5]")
    else:
        assert payload["data"]["package_id"] == package_dir.name


def test_cross_host_import_rejects_invalid_generated_acknowledgement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, _, package_dir = _exported(tmp_path, "invalid ack")
    destination = init_repo(tmp_path / "destination")
    monkeypatch.setenv("ETHOS_ACTOR", HOLDER_B)
    validate = handoff.handoff_package.validate_schema_instance
    monkeypatch.setattr(
        handoff.handoff_package,
        "validate_schema_instance",
        lambda name, payload, **kwargs: (
            {"ok": False, "required_gaps": ["invalid"]}
            if name == "handoff-acknowledgement.schema.json"
            else validate(name, payload, **kwargs)
        ),
    )

    payload = handoff.import_cross_host_handoff(
        root=destination,
        package=package_dir,
        target_holder_ref=HOLDER_B,
        apply=True,
    )

    assert payload["required_gaps"] == [
        "handoff_import_failed:handoff_acknowledgement_invalid:invalid"
    ]


def test_cross_host_import_reports_incomplete_compensation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, _, package_dir = _exported(tmp_path, "failed cleanup")
    destination = init_repo(tmp_path / "destination")
    monkeypatch.setenv("ETHOS_ACTOR", HOLDER_B)
    monkeypatch.setattr(
        handoff.handoff_package,
        "acquire_lease",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError()),
    )
    original_run_git = handoff.handoff_package.run_git

    def keep_ref(root: Path, *args: str, **kwargs):
        if args[:3] == ("update-ref", "-d", "refs/heads/work/feature"):
            return subprocess.CompletedProcess(["git", *args], 0, "", "")
        return original_run_git(root, *args, **kwargs)

    monkeypatch.setattr(handoff.handoff_package, "run_git", keep_ref)

    with pytest.raises(ValueError, match="handoff_import_compensation_failed"):
        handoff.handoff_package.apply_handoff_import(
            destination=destination,
            package=package_dir,
            manifest=_manifest(package_dir),
            target_holder_ref=HOLDER_B,
        )
