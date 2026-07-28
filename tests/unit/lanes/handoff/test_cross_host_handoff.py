from __future__ import annotations

import hashlib
import json
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

import ethos.adapters.mutation.lane_lifecycle.handoff.destination_import as destination_import
from ethos.adapters.mutation.lane_lifecycle.handoff.transfer import export_cross_host_handoff
from ethos.adapters.mutation.lane_lifecycle.handoff.transfer import import_cross_host_handoff
from ethos.adapters.mutation.lane_lifecycle.handoff.transfer import revoke_cross_host_source
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.store.state.lease.projection import LeaseObservation
from ethos.adapters.store.state.lease.projection import observe_lease
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.coordination import CrossHostHandoffExportRequest
from ethos.contracts.coordination import CrossHostHandoffImportRequest
from ethos.contracts.coordination import CrossHostHandoffSourceRevocationRequest
from tests.support.contract_helpers import start_adopted_candidate
from tests.support.contract_helpers import start_adopted_work_lane


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
    for object_id in object_ids:
        assert (
            subprocess.run(
                ["git", "cat-file", "-e", object_id],
                cwd=destination,
                check=False,
            ).returncode
            == 0
        )


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
    """Fault-injection inputs for one destination handoff import."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    stage: str = Field(min_length=1)
    destination: str = Field(min_length=1)
    package: str = Field(min_length=1)
    target_holder: str = Field(min_length=1)


def _import_with_fault(
    request: _ImportFaultRequest,
    *,
    preserved_objects: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, object]:
    destination = Path(request.destination)
    package = Path(request.package)
    real_run_git = destination_import.run_git
    expected_inventory: dict[str, str] = {}
    with monkeypatch.context() as faults:
        if request.stage == "install":
            real_link = destination_import.os.link
            calls = 0

            def fail_install(source: object, target: object) -> None:
                nonlocal calls, expected_inventory
                if calls:
                    message = "forced-install-failure"
                    raise OSError(message)
                preserved_objects.append(
                    _write_object(destination, "concurrent destination object during install\n")
                )
                expected_inventory = _object_inventory(destination)
                real_link(source, target)
                calls += 1

            faults.setattr(destination_import.os, "link", fail_install)
        else:
            failed = False

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
        report = import_cross_host_handoff(
            CrossHostHandoffImportRequest(
                root=destination.as_posix(),
                package=package.as_posix(),
                target_holder_ref=request.target_holder,
                apply=True,
            )
        )
    assert _object_inventory(destination) == expected_inventory
    return report


def _import_with_uncertain_effect(
    request: _ImportFaultRequest,
    *,
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, object]:
    destination = Path(request.destination)
    package = Path(request.package)
    real_run_git = destination_import.run_git
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
        return import_cross_host_handoff(
            CrossHostHandoffImportRequest(
                root=destination.as_posix(),
                package=package.as_posix(),
                target_holder_ref=request.target_holder,
                apply=True,
            )
        )


def _export_handoff_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source_holder: str,
    target_holder: str,
    branch: str,
) -> tuple[Any, Any, Path, str, dict[str, object]]:
    source = start_adopted_work_lane(tmp_path / "source", name="handoff", holder_ref=source_holder)
    destination, _candidate = start_adopted_candidate(tmp_path / "destination")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=source.worktree,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    lease = leases_by_branch(source.worktree)[branch]
    export_arguments = {
        "root": source.worktree.as_posix(),
        "branch": branch,
        "holder_ref": source_holder,
        "target_holder_ref": target_holder,
        "lease_id": str(lease["lease_id"]),
        "epoch": int(lease["epoch"]),
        "expected_expires_at": str(lease["expires_at"]),
        "expected_payload_sha256": str(lease["payload_sha256"]),
        "expect_head": head,
        "context_text": "Continue only after destination validates the package.",
        "context_file": None,
        "output_root": (tmp_path / "packages").as_posix(),
        "apply": True,
    }
    monkeypatch.setenv("ETHOS_ACTOR", source_holder)
    exported = export_cross_host_handoff(CrossHostHandoffExportRequest(**export_arguments))
    assert exported["ok"] is True
    assert exported["manifest"]["base_commitment_digest"] == lease["base_commitment_digest"]
    package = Path(str(exported["package_path"]))
    repeated_export = export_cross_host_handoff(CrossHostHandoffExportRequest(**export_arguments))
    assert (repeated_export["ok"], repeated_export["package_id"]) == (
        True,
        exported["package_id"],
    )
    return source, destination, package, head, lease


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
    assert rolled_back["ok"] is False
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
    assert rolled_back["ok"] is False
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
    head = str(lease["expected_head"])
    imported = import_cross_host_handoff(
        CrossHostHandoffImportRequest(
            root=destination.as_posix(),
            package=package.as_posix(),
            target_holder_ref="agent:test:case:target",
            apply=True,
        )
    )
    assert imported["ok"] is True
    assert imported["lease"]["base_commitment_digest"] == lease["base_commitment_digest"]
    assert imported["acknowledgement"]["base_commitment_digest"] == lease["base_commitment_digest"]
    acknowledgement = package.parent / "acknowledgement.json"
    acknowledgement.write_text(
        json.dumps(imported["acknowledgement"], sort_keys=True) + "\n", encoding="utf-8"
    )
    monkeypatch.setenv("ETHOS_ACTOR", source_holder)
    revoked = revoke_cross_host_source(
        CrossHostHandoffSourceRevocationRequest(
            root=source.worktree.as_posix(),
            package=package.as_posix(),
            acknowledgement=acknowledgement.as_posix(),
            holder_ref=source_holder,
            lease_id=str(lease["lease_id"]),
            epoch=int(lease["epoch"]),
            expected_expires_at=str(lease["expires_at"]),
            expected_payload_sha256=str(lease["payload_sha256"]),
            expect_head=head,
            apply=True,
        )
    )
    assert (revoked["ok"], revoked["state"]) == (True, "source_revoked")
    assert branch not in leases_by_branch(source.worktree)


def test_handoff_import_rejects_object_format_mismatch_before_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "destination.git"
    destination.mkdir()
    subprocess.run(
        ["git", "init", "--bare", "--object-format=sha256", "."],
        cwd=destination,
        check=True,
        text=True,
        capture_output=True,
    )
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    manifest = {
        "package_id": f"handoff:{'c' * 64}",
        "source_lane_ref": "work/example",
        "source_head": "a" * 40,
        "source_tree": "b" * 40,
    }
    git_calls: list[tuple[str, ...]] = []
    real_run_git = destination_import.run_git

    def observed_git(root: Path, *args: str, **kwargs: Any) -> subprocess.CompletedProcess[Any]:
        git_calls.append(args)
        return real_run_git(root, *args, **kwargs)

    @contextmanager
    def package_snapshot(**_kwargs: object):
        yield snapshot

    def unexpected_lease(*_args: object, **_kwargs: object) -> dict[str, object]:
        message = "object-format mismatch must precede Lease reservation"
        raise AssertionError(message)

    monkeypatch.setattr(destination_import, "run_git", observed_git)
    monkeypatch.setattr(destination_import, "verified_package_snapshot", package_snapshot)
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
    source, destination, package, head, lease = _export_handoff_fixture(
        tmp_path, monkeypatch, source_holder, target_holder, branch
    )

    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:wrong")
    denied = import_cross_host_handoff(
        CrossHostHandoffImportRequest(
            root=destination.as_posix(),
            package=package.as_posix(),
            target_holder_ref=target_holder,
            apply=True,
        )
    )
    assert denied["ok"] is False
    assert "handoff_target_actor_mismatch" in denied["required_gaps"]

    expected_worktree = destination.with_name(f"{destination.name}-{branch.replace('/', '-')}")
    object_probe = ["git", "cat-file", "-e", f"{head}^{{commit}}"]
    preexisting_object = _write_object(destination, "preexisting destination object\n")
    preserved_objects = [preexisting_object]

    assert subprocess.run(object_probe, cwd=destination, check=False).returncode != 0
    with monkeypatch.context() as faults:

        def fail_reservation(*_args: object, **_kwargs: object) -> dict[str, object]:
            msg = "forced-lease-failure"
            raise ValueError(msg)

        faults.setattr(destination_import, "acquire_lease", fail_reservation)
        monkeypatch.setenv("ETHOS_ACTOR", target_holder)
        rolled_back = import_cross_host_handoff(
            CrossHostHandoffImportRequest(
                root=destination.as_posix(),
                package=package.as_posix(),
                target_holder_ref=target_holder,
                apply=True,
            )
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
