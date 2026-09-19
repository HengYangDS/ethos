"""Transfer exact lane content with authority, compensation and source revocation."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
from contextlib import closing
from contextlib import contextmanager
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

import ethos.adapters.mutation.lane_lifecycle.handoff.destination_import as destination_import
import ethos.adapters.mutation.lane_lifecycle.handoff.destination_objects as destination_objects
import ethos.adapters.repo.git_effects as git_effects
from ethos.adapters.mutation.lane_lifecycle.handoff.transfer import import_cross_host_handoff
from ethos.adapters.mutation.lane_lifecycle.handoff.transfer import revoke_cross_host_source
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.store.state.lease.projection import LeaseObservation
from ethos.adapters.store.state.lease.projection import observe_lease
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.coordination import CrossHostHandoffImportRequest
from ethos.contracts.coordination import CrossHostHandoffSourceRevocationRequest
from tests.support.governed_repository import git
from tests.unit.lanes.handoff.support import export_handoff_fixture


def _write_object(destination: Path, content: str) -> str:
    return subprocess.run(
        ["git", "hash-object", "-w", "--stdin"],
        cwd=destination,
        input=content,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


def _assert_objects_exist(destination: Path, object_ids: list[str]) -> None:
    assert not any(git(destination, "cat-file", "-e", object_id) for object_id in object_ids)


def _object_inventory(destination: Path) -> dict[str, str]:
    objects = Path(
        subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-path", "objects"],
            cwd=destination,
            check=True,
            text=True,
            capture_output=True,
        ).stdout.strip()
    )
    return {
        path.relative_to(objects).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in objects.rglob("*")
        if path.is_file() and not path.relative_to(objects).parts[0].startswith("handoff-import-")
    }


class _ImportFaultRequest(BaseModel):
    stage: str
    destination: str
    package: str
    target_holder: str


def _import_request(destination: Path, package: Path, holder: str) -> CrossHostHandoffImportRequest:
    return CrossHostHandoffImportRequest(
        root=destination.as_posix(),
        package=package.as_posix(),
        target_holder_ref=holder,
        apply=True,
    )


def _revoke_request(
    source: Path, package: Path, acknowledgement: Path, holder: str, lease: dict[str, object]
) -> CrossHostHandoffSourceRevocationRequest:
    return CrossHostHandoffSourceRevocationRequest(
        root=source.as_posix(),
        package=package.as_posix(),
        acknowledgement=acknowledgement.as_posix(),
        holder_ref=holder,
        generation=int(lease["generation"]),
        expires_at=str(lease["expires_at"]),
        expect_head=git(source, "rev-parse", "HEAD"),
        apply=True,
    )


def _import_with_fault(
    request: _ImportFaultRequest,
    *,
    preserved_objects: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, object]:
    destination = Path(request.destination)
    package = Path(request.package)
    expected_inventory: dict[str, str] = {}
    with monkeypatch.context() as faults:
        if request.stage == "install":
            real_link = destination_objects.os.link
            calls = 0

            def fail_install(source: object, target: object) -> None:
                nonlocal calls, expected_inventory
                installing_pack = (
                    Path(target).parent.name == "pack" and Path(source).parent.name == "pack"
                )
                if not installing_pack:
                    real_link(source, target)
                    return
                if calls == 1:
                    calls += 1
                    message = "forced-install-failure"
                    raise OSError(message)
                preserved_objects.append(
                    _write_object(destination, "concurrent destination object during install\n")
                )
                expected_inventory = _object_inventory(destination)
                real_link(source, target)
                calls += 1

            faults.setattr(destination_objects.os, "link", fail_install)
        else:
            failed = False
            real_run_git = destination_import.run_git

            def fail_git(
                root: Path,
                *args: str,
                failed_stage: str = request.stage,
                **kwargs: Any,
            ) -> subprocess.CompletedProcess[Any]:
                nonlocal failed, expected_inventory
                targeted = (
                    (failed_stage == "ref" and args[:2] == ("update-ref", "--stdin"))
                    or (failed_stage == "worktree" and args[:2] == ("worktree", "add"))
                    or (
                        failed_stage == "commit"
                        and root.name.endswith("work-handoff")
                        and args == ("rev-parse", "HEAD")
                    )
                    or (failed_stage == "index-pack" and args[:1] == ("index-pack",))
                )
                if "prune" in args:
                    message = "handoff compensation must not prune"
                    raise AssertionError(message)
                if targeted and not failed:
                    failed = True
                    preserved_objects.append(
                        _write_object(
                            destination,
                            f"concurrent destination object during {failed_stage}\n",
                        )
                    )
                    expected_inventory = _object_inventory(destination)
                    message = f"forced-{failed_stage}-failure"
                    raise ValueError(message)
                return real_run_git(root, *args, **kwargs)

            faults.setattr(destination_import, "run_git", fail_git)
            faults.setattr(destination_objects, "run_git", fail_git)
            if request.stage == "ref":
                faults.setattr(git_effects, "run_git", fail_git)
        report = import_cross_host_handoff(
            _import_request(destination, package, request.target_holder)
        )
    if not expected_inventory:
        message = f"fault_not_injected:{request.stage}:{report}"
        raise AssertionError(message)
    assert expected_inventory.items() <= _object_inventory(destination).items()
    return report


def _import_with_uncertain_effect(
    request: _ImportFaultRequest,
    *,
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, object]:
    destination = Path(request.destination)
    package = Path(request.package)
    real_acquire = destination_import.acquire_lease
    failed = False
    with monkeypatch.context() as faults:
        if request.stage == "lease":

            def acquire_then_fail(*args: object, **kwargs: Any) -> dict[str, object]:
                real_acquire(*args, **kwargs)
                message = "forced-lease-uncertain"
                raise ValueError(message)

            faults.setattr(destination_import, "acquire_lease", acquire_then_fail)
        else:
            real_run_git = destination_import.run_git

            def run_then_fail(
                root: Path, *args: str, **kwargs: Any
            ) -> subprocess.CompletedProcess[Any]:
                nonlocal failed
                completed = real_run_git(root, *args, **kwargs)
                targeted = (request.stage == "ref" and args[:2] == ("update-ref", "--stdin")) or (
                    request.stage == "worktree" and args[:2] == ("worktree", "add")
                )
                if targeted and not failed:
                    failed = True
                    message = f"forced-{request.stage}-uncertain"
                    raise ValueError(message)
                return completed

            faults.setattr(destination_import, "run_git", run_then_fail)
            if request.stage == "ref":
                faults.setattr(git_effects, "run_git", run_then_fail)
        return import_cross_host_handoff(
            _import_request(destination, package, request.target_holder)
        )


def _assert_failed_import_is_compensated(
    rolled_back: dict[str, object],
    *,
    expected_worktree: Path,
    destination: Path,
    branch: str,
    object_probe: list[str],
    preserved_objects: list[str],
    stage: str,
) -> None:
    assert rolled_back["verdict"] == "block"
    assert "ok" not in rolled_back
    assert rolled_back["mutation"]["decision"]["verdict"] == rolled_back["verdict"]
    assert f"handoff_import_failed:forced-{stage}-failure" in rolled_back["required_gaps"]
    assert subprocess.run(object_probe, cwd=destination, check=False).returncode != 0
    assert not expected_worktree.exists()
    assert (
        subprocess.run(
            ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
            cwd=destination,
            check=False,
        ).returncode
        == 1
    )
    assert observe_lease(state_database(destination), branch).state == "missing"
    _assert_objects_exist(destination, preserved_objects)


def _assert_uncertain_import_is_compensated(
    rolled_back: dict[str, object],
    *,
    expected_worktree: Path,
    destination: Path,
    branch: str,
    object_probe: list[str],
    stage: str,
) -> None:
    assert rolled_back["verdict"] == "block"
    assert "ok" not in rolled_back
    assert rolled_back["mutation"]["decision"]["verdict"] == rolled_back["verdict"]
    assert f"handoff_import_failed:forced-{stage}-uncertain" in rolled_back["required_gaps"]
    assert not expected_worktree.exists()
    assert observe_lease(state_database(destination), branch).state == "missing"
    assert subprocess.run(object_probe, cwd=destination, check=False).returncode != 0


def _assert_source_revoked(
    monkeypatch: pytest.MonkeyPatch,
    source: Any,
    package: Path,
    lease: dict[str, object],
    destination: Path,
) -> None:
    source_holder = "agent:test:case:source"
    branch = "work/handoff"
    request = _import_request(destination, package, "agent:test:case:target")
    imported = import_cross_host_handoff(request)
    assert (imported["verdict"], imported.get("ok")) == ("pass", None)
    assert imported["object_attestation"]["payload"]["body"]["result"]["state"] == "applied"
    assert imported["mutation"]["decision"]["verdict"] == imported["verdict"]
    assert imported["lease"]["lane_ref"] == branch
    assert imported["lease"]["holder_ref"] == "agent:test:case:target"
    first_generation = imported["lease"]["generation"]
    assert imported["acknowledgement"]["destination_lease_generation"] == first_generation
    repeated_import = import_cross_host_handoff(request)
    assert repeated_import["verdict"] == "pass"
    assert (
        repeated_import["object_attestation"]["payload"]["body"]["result"]["state"] == "recognized"
    )
    assert repeated_import["lease"] == imported["lease"]
    database = state_database(destination)
    expired_at = datetime.now(UTC) - timedelta(seconds=1)
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute(
            "update leases set expires_at = ? where lane_ref = ?",
            (expired_at.isoformat(), branch),
        )
    resumed_import = import_cross_host_handoff(request)
    assert resumed_import["verdict"] == "pass"
    assert resumed_import["lease"]["generation"] == first_generation + 1
    assert resumed_import["lease"]["holder_ref"] == "agent:test:case:target"
    acknowledgement = package.parent / "acknowledgement.json"
    acknowledgement.write_text(
        json.dumps(resumed_import["acknowledgement"], sort_keys=True) + "\n", encoding="utf-8"
    )
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("delete from leases where lane_ref = ?", (branch,))
    orphan = import_cross_host_handoff(request)
    assert orphan["verdict"] == "block"
    assert orphan["required_gaps"] == ["handoff_import_failed:handoff_destination_orphan_carrier"]
    assert observe_lease(database, branch).state == "missing"
    monkeypatch.setenv("ETHOS_ACTOR", source_holder)
    request = _revoke_request(source.worktree, package, acknowledgement, source_holder, lease)
    revoked = revoke_cross_host_source(request)
    assert revoked["verdict"] == "pass"
    assert revoked["state"] == "source_revoked"
    assert revoked["mutation"]["decision"]["verdict"] == revoked["verdict"]
    assert revoked["receipt"]["generation"] == lease["generation"]
    assert branch not in leases_by_branch(source.worktree)
    repeated_revoke = revoke_cross_host_source(request)
    assert repeated_revoke["verdict"] == "block"
    assert repeated_revoke["required_gaps"] == ["handoff_source_lease_missing"]
    assert repeated_revoke["receipt"] == {}
    mismatched = revoke_cross_host_source(request.model_copy(update={"generation": 99}))
    assert mismatched["verdict"] == "block"
    assert "handoff_source_lease_mismatch" in mismatched["required_gaps"]


def test_handoff_source_revoke_rejects_live_generation_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_holder = "agent:test:case:source"
    source, destination, package, _head, lease = export_handoff_fixture(
        tmp_path,
        monkeypatch,
        source_holder,
        "agent:test:case:target",
        "work/handoff",
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:target")
    imported = import_cross_host_handoff(
        _import_request(destination, package, "agent:test:case:target")
    )
    acknowledgement = package.parent / "acknowledgement.json"
    acknowledgement.write_text(
        json.dumps(imported["acknowledgement"], sort_keys=True) + "\n", encoding="utf-8"
    )
    database = state_database(source.worktree)
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute(
            "update leases set generation = generation + 1 where lane_ref = ?",
            ("work/handoff",),
        )
    monkeypatch.setenv("ETHOS_ACTOR", source_holder)
    report = revoke_cross_host_source(
        _revoke_request(source.worktree, package, acknowledgement, source_holder, lease)
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["lease_generation_stale"]
    assert observe_lease(database, "work/handoff").state == "valid"


def test_handoff_import_rejects_tampered_source_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_holder = "agent:test:case:source"
    target_holder = "agent:test:case:target"
    _source, destination, package, _head, _lease = export_handoff_fixture(
        tmp_path, monkeypatch, source_holder, target_holder, "work/handoff"
    )
    manifest_path = package / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source_tree"] = "0" * 40
    body = {key: value for key, value in manifest.items() if key != "package_id"}
    canonical_body = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    package_id = f"handoff:{hashlib.sha256(canonical_body).hexdigest()}"
    manifest["package_id"] = package_id
    manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
    package = package.rename(package.with_name(package_id))
    monkeypatch.setenv("ETHOS_ACTOR", target_holder)

    report = import_cross_host_handoff(_import_request(destination, package, target_holder))

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["handoff_import_failed:handoff_bundle_identity_mismatch"]
    assert report["lease"] == {}
    assert not (destination.parent / f"{destination.name}-work-handoff").exists()


def test_handoff_import_rejects_object_format_mismatch_before_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "destination.git"
    destination.mkdir()
    git(destination, "init", "--bare", "--object-format=sha256", ".")
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    manifest = {
        "package_id": f"handoff:{'c' * 64}",
        "source_lane_ref": "work/example",
        "source_head": "a" * 40,
        "source_tree": "b" * 40,
    }
    git_calls: list[tuple[str, ...]] = []
    real_run_git = destination_objects.run_git

    def observed_git(root: Path, *args: str, **kwargs: Any) -> subprocess.CompletedProcess[Any]:
        git_calls.append(args)
        return real_run_git(root, *args, **kwargs)

    @contextmanager
    def package_snapshot(**_kwargs: object):
        yield snapshot

    def unexpected_lease(*_args: object, **_kwargs: object) -> dict[str, object]:
        message = "object-format mismatch must precede Lease reservation"
        raise AssertionError(message)

    monkeypatch.setattr(destination_objects, "run_git", observed_git)
    monkeypatch.setattr(destination_objects, "verified_package_snapshot", package_snapshot)
    monkeypatch.setattr(
        destination_import,
        "observe_lease",
        lambda _database, subject: LeaseObservation(state="missing", subject=subject),
    )
    monkeypatch.setattr(destination_import, "state_database", lambda _root: tmp_path / "state.db")
    monkeypatch.setattr(destination_import, "acquire_lease", unexpected_lease)

    with pytest.raises(ValueError, match=r"^handoff_object_format_mismatch$"):
        destination_import.apply_handoff_import(
            destination=destination,
            package=tmp_path / "package",
            manifest=manifest,
            target_holder_ref="agent:test:case:target",
        )

    assert git_calls == [("rev-parse", "--show-object-format")]


def test_cross_host_handoff_enforces_authority_compensates_and_revokes_exact_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_holder = "agent:test:case:source"
    target_holder = "agent:test:case:target"
    branch = "work/handoff"
    source, destination, package, head, lease = export_handoff_fixture(
        tmp_path, monkeypatch, source_holder, target_holder, branch
    )

    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:wrong")
    denied = import_cross_host_handoff(_import_request(destination, package, target_holder))
    assert denied["verdict"] == "block"
    assert "ok" not in denied
    assert denied["mutation"]["decision"]["verdict"] == denied["verdict"]
    assert "handoff_target_actor_mismatch" in denied["required_gaps"]

    expected_worktree = destination.with_name(f"{destination.name}-{branch.replace('/', '-')}")
    object_probe = ["git", "cat-file", "-e", f"{head}^{{commit}}"]
    preexisting_object = _write_object(destination, "preexisting destination object\n")
    preserved_objects = [preexisting_object]

    assert subprocess.run(object_probe, cwd=destination, check=False).returncode != 0
    with monkeypatch.context() as faults:

        def fail_reservation(*_args: object, **_kwargs: object) -> dict[str, object]:
            msg = "forced-lease-failure"
            raise RuntimeError(msg)

        faults.setattr(destination_import, "acquire_lease", fail_reservation)
        monkeypatch.setenv("ETHOS_ACTOR", target_holder)
        rolled_back = import_cross_host_handoff(
            _import_request(destination, package, target_holder)
        )
    _assert_failed_import_is_compensated(
        rolled_back,
        expected_worktree=expected_worktree,
        destination=destination,
        branch=branch,
        object_probe=object_probe,
        preserved_objects=preserved_objects,
        stage="lease",
    )

    for stage in ("ref", "worktree", "commit", "index-pack", "install"):
        rolled_back = _import_with_fault(
            _ImportFaultRequest(
                stage=stage,
                destination=destination.as_posix(),
                package=package.as_posix(),
                target_holder=target_holder,
            ),
            preserved_objects=preserved_objects,
            monkeypatch=monkeypatch,
        )
        _assert_failed_import_is_compensated(
            rolled_back,
            expected_worktree=expected_worktree,
            destination=destination,
            branch=branch,
            object_probe=object_probe,
            preserved_objects=preserved_objects,
            stage=stage,
        )

    for stage in ("lease", "ref", "worktree"):
        rolled_back = _import_with_uncertain_effect(
            _ImportFaultRequest(
                stage=stage,
                destination=destination.as_posix(),
                package=package.as_posix(),
                target_holder=target_holder,
            ),
            monkeypatch=monkeypatch,
        )
        _assert_uncertain_import_is_compensated(
            rolled_back,
            expected_worktree=expected_worktree,
            destination=destination,
            branch=branch,
            object_probe=object_probe,
            stage=stage,
        )

    _assert_source_revoked(
        monkeypatch,
        source,
        package,
        lease,
        destination,
    )
