from __future__ import annotations

import os
import stat
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

import ethos.adapters.mutation.lane_lifecycle.handoff.destination_import as destination_import
import ethos.adapters.mutation.lane_lifecycle.handoff.package as handoff_package
import ethos.adapters.repo.dirty.change_provenance as change_provenance
from ethos.adapters.store.state.lease.projection import LeaseObservation
from ethos.contracts.coordination import CrossHostHandoff
from ethos.contracts.coordination import HolderRef


@pytest.mark.parametrize("width", [40, 64])
def test_cross_host_handoff_transfers_content_not_source_lease(width: int) -> None:
    handoff = CrossHostHandoff(
        source_lane_ref="work/example",
        source_head="a" * width,
        source_tree="b" * width,
        target_holder_ref=HolderRef.parse("agent:other:run:two"),
        context_digest="c" * 64,
        dirty_content_sha256="f" * 64,
        source_lease_id="lease:one",
        source_lease_epoch=3,
        source_lease_expires_at="2026-07-20T00:00:00+00:00",
        source_lease_payload_sha256="e" * 64,
        base_change_contract_digest="f" * 64,
        source_holder_ref=HolderRef.parse("agent:source:run:one"),
        artifacts=({"path": "repository.bundle", "sha256": "d" * 64, "kind": "git_bundle"},),
    )

    payload = handoff.to_payload()
    assert payload["source_head"] == "a" * width
    assert payload["source_tree"] == "b" * width
    assert payload["target_holder_ref"] == "agent:other:run:two"
    assert payload["dirty_content_sha256"] == "f" * 64
    assert payload["base_change_contract_digest"] == "f" * 64
    assert payload["transfers_source_lease"] is False
    assert payload["destination_creates_local_incarnation"] is True
    assert payload["source_lease_binding"]["epoch"] == 3
    assert payload["source_lease_binding"]["expires_at"] == "2026-07-20T00:00:00+00:00"
    assert payload["source_lease_binding"]["payload_sha256"] == "e" * 64
    assert payload["truth_boundary"] == "content_addressed_context_until_promoted"
    assert CrossHostHandoff.model_fields["source_lease_expires_at"].is_required()
    assert CrossHostHandoff.model_fields["source_lease_payload_sha256"].is_required()
    assert CrossHostHandoff.model_fields["base_change_contract_digest"].is_required()


def test_cross_host_handoff_rejects_missing_base_change_contract_digest() -> None:
    with pytest.raises(ValidationError):
        CrossHostHandoff(
            source_lane_ref="work/example",
            source_head="a" * 40,
            source_tree="b" * 40,
            target_holder_ref=HolderRef.parse("agent:other:run:two"),
            context_digest="c" * 64,
            dirty_content_sha256="f" * 64,
            source_lease_id="lease:one",
            source_lease_epoch=3,
            source_lease_expires_at="2026-07-20T00:00:00+00:00",
            source_lease_payload_sha256="e" * 64,
            source_holder_ref=HolderRef.parse("agent:source:run:one"),
        )


@pytest.mark.parametrize("width", [41, 63])
def test_cross_host_handoff_rejects_intermediate_oid_widths(width: int) -> None:
    with pytest.raises(ValidationError):
        CrossHostHandoff(
            source_lane_ref="work/example",
            source_head="a" * width,
            source_tree="b" * width,
            target_holder_ref=HolderRef.parse("agent:other:run:two"),
            context_digest="c" * 64,
            dirty_content_sha256="f" * 64,
            source_lease_id="lease:one",
            source_lease_epoch=3,
            source_lease_expires_at="2026-07-20T00:00:00+00:00",
            source_lease_payload_sha256="e" * 64,
            base_change_contract_digest="f" * 64,
            source_holder_ref=HolderRef.parse("agent:source:run:one"),
        )


def test_cross_host_handoff_rejects_legacy_dirty_disposition() -> None:
    with pytest.raises(ValidationError):
        CrossHostHandoff(
            source_lane_ref="work/example",
            source_head="a" * 40,
            source_tree="b" * 40,
            target_holder_ref=HolderRef.parse("agent:other:run:two"),
            context_digest="c" * 64,
            dirty_content_sha256="f" * 64,
            dirty_disposition="preserved",
            source_lease_id="lease:one",
            source_lease_epoch=3,
            source_lease_expires_at="2026-07-20T00:00:00+00:00",
            source_lease_payload_sha256="e" * 64,
            base_change_contract_digest="f" * 64,
            source_holder_ref=HolderRef.parse("agent:source:run:one"),
        )


@pytest.mark.parametrize("epoch", [True, "1", 1.0])
def test_cross_host_handoff_rejects_coercive_lease_epochs(epoch: object) -> None:
    with pytest.raises(ValidationError):
        CrossHostHandoff(
            source_lane_ref="work/example",
            source_head="a" * 40,
            source_tree="b" * 40,
            target_holder_ref=HolderRef.parse("agent:other:run:two"),
            context_digest="c" * 64,
            dirty_content_sha256="f" * 64,
            source_lease_id="lease:one",
            source_lease_epoch=epoch,
            source_lease_expires_at="2026-07-20T00:00:00+00:00",
            source_lease_payload_sha256="e" * 64,
            base_change_contract_digest="f" * 64,
            source_holder_ref=HolderRef.parse("agent:source:run:one"),
        )


@pytest.mark.parametrize(
    "artifact",
    [
        {"path": "../repository.bundle", "sha256": "d" * 64, "kind": "git_bundle"},
        {"path": "repository.bundle", "sha256": "d" * 64, "kind": "tracked_patch"},
        {
            "path": "repository.bundle",
            "sha256": "d" * 64,
            "kind": "git_bundle",
            "legacy": "field",
        },
    ],
)
def test_cross_host_handoff_rejects_noncanonical_artifacts(
    artifact: dict[str, str],
) -> None:
    with pytest.raises(ValidationError):
        CrossHostHandoff(
            source_lane_ref="work/example",
            source_head="a" * 40,
            source_tree="b" * 40,
            target_holder_ref=HolderRef.parse("agent:other:run:two"),
            context_digest="c" * 64,
            dirty_content_sha256="f" * 64,
            source_lease_id="lease:one",
            source_lease_epoch=3,
            source_lease_expires_at="2026-07-20T00:00:00+00:00",
            source_lease_payload_sha256="e" * 64,
            base_change_contract_digest="f" * 64,
            source_holder_ref=HolderRef.parse("agent:source:run:one"),
            artifacts=(artifact,),
        )


def test_handoff_export_rejects_a_bundle_from_another_generation(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    handoff = CrossHostHandoff(
        source_lane_ref="work/example",
        source_head="a" * 40,
        source_tree="b" * 40,
        target_holder_ref=HolderRef.parse("agent:other:run:two"),
        context_digest="c" * 64,
        dirty_content_sha256="d" * 64,
        source_lease_id="lease:one",
        source_lease_epoch=1,
        source_lease_expires_at="2026-07-21T00:00:00+00:00",
        source_lease_payload_sha256="e" * 64,
        base_change_contract_digest="f" * 64,
        source_holder_ref=HolderRef.parse("agent:source:run:one"),
    )

    def run_git(_root, *args, **_kwargs):
        stdout = (
            f"{'f' * 40} refs/heads/work/example\n" if args[:2] == ("bundle", "list-heads") else ""
        )
        return SimpleNamespace(stdout=stdout)

    monkeypatch.setattr(handoff_package, "run_git", run_git)
    monkeypatch.setattr(
        handoff_package,
        "_artifact",
        lambda path, _root, kind: {"path": path.name, "sha256": "0" * 64, "kind": kind},
    )
    monkeypatch.setattr(handoff_package, "_require_schema", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(handoff_package, "_verify_export_snapshot", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(handoff_package, "_publish_package", lambda *_args, **_kwargs: None)

    with pytest.raises(ValueError, match="handoff_bundle_identity_mismatch"):
        handoff_package.write_handoff_package(
            repo=tmp_path,
            handoff=handoff,
            context="context",
            output_root=tmp_path / "output",
        )


def test_handoff_manifest_rejects_a_symlinked_manifest(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = tmp_path / "handoff:package"
    package.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text("{}\n", encoding="utf-8")
    (package / "manifest.json").symlink_to(outside)
    monkeypatch.setattr(
        handoff_package,
        "validate_schema_instance",
        lambda *_args, **_kwargs: {"ok": True, "required_gaps": []},
    )

    _, gaps = handoff_package.verified_handoff_manifest(package=package, root=tmp_path)

    assert gaps == ["handoff_manifest_unsafe"]


@pytest.mark.parametrize("state", ["valid", "expired", "unknown"])
def test_handoff_import_rejects_destination_lease_before_git_effects(
    tmp_path, monkeypatch: pytest.MonkeyPatch, state: str
) -> None:
    branch = "work/example"
    destination = tmp_path / "destination"
    destination.mkdir()
    git_calls: list[tuple[str, ...]] = []

    monkeypatch.setattr(
        destination_import,
        "observe_lease",
        lambda _database, subject: LeaseObservation(state=state, subject=subject),
        raising=False,
    )
    monkeypatch.setattr(
        destination_import, "state_database", lambda _root: tmp_path / "state.sqlite"
    )

    def unexpected_git(_root, *args, **_kwargs):
        git_calls.append(args)
        raise AssertionError

    monkeypatch.setattr(destination_import, "run_git", unexpected_git)

    with pytest.raises(ValueError, match=r"^handoff_import_lease_conflict$"):
        destination_import.apply_handoff_import(
            destination=destination,
            package=tmp_path / "package",
            manifest={
                "package_id": f"handoff:{'c' * 64}",
                "source_lane_ref": branch,
                "source_head": "a" * 40,
                "base_change_contract_digest": "b" * 64,
            },
            target_holder_ref="agent:test:case:target",
        )

    assert git_calls == []


def test_dirty_content_digest_frames_path_and_content(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "a").write_bytes(b"bc")
    (tmp_path / "ab").write_bytes(b"c")

    selected = b"a\0"

    def run_git(_root, *args, **kwargs):
        assert kwargs["text"] is False
        return SimpleNamespace(stdout=b"" if args[0] == "diff" else selected)

    monkeypatch.setattr(change_provenance, "run_git", run_git)
    first = change_provenance.dirty_content_sha256(tmp_path)
    selected = b"ab\0"

    assert change_provenance.dirty_content_sha256(tmp_path) != first


def test_dirty_content_digest_rejects_an_untracked_symlink(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outside = tmp_path.parent / "outside"
    outside.write_bytes(b"external")
    (tmp_path / "link").symlink_to(outside)

    monkeypatch.setattr(
        change_provenance,
        "run_git",
        lambda _root, *args, **_kwargs: SimpleNamespace(
            stdout=b"" if args[0] == "diff" else b"link\0"
        ),
    )

    with pytest.raises(ValueError, match="dirty_content_unsafe_path:link"):
        change_provenance.dirty_content_sha256(tmp_path)


@pytest.mark.parametrize("drift", ["patch", "inventory"])
def test_dirty_content_digest_rejects_snapshot_drift(
    tmp_path, monkeypatch: pytest.MonkeyPatch, drift: str
) -> None:
    (tmp_path / "file").write_bytes(b"content")
    calls = {"diff": 0, "ls-files": 0}

    def run_git(_root, *args, **_kwargs):
        command = args[0]
        calls[command] += 1
        if command == "diff":
            changed = drift == "patch" and calls[command] == 2
            return SimpleNamespace(stdout=b"changed" if changed else b"")
        changed = drift == "inventory" and calls[command] == 2
        return SimpleNamespace(stdout=b"other\0" if changed else b"file\0")

    monkeypatch.setattr(change_provenance, "run_git", run_git)

    with pytest.raises(ValueError, match="dirty_content_snapshot_drift"):
        change_provenance.dirty_content_sha256(tmp_path)


def test_dirty_content_digest_rejects_a_symlinked_root(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_root = tmp_path / "real"
    real_root.mkdir()
    (real_root / "file").write_bytes(b"content")
    linked_root = tmp_path / "linked"
    linked_root.symlink_to(real_root, target_is_directory=True)
    monkeypatch.setattr(
        change_provenance,
        "run_git",
        lambda _root, *args, **_kwargs: SimpleNamespace(
            stdout=b"" if args[0] == "diff" else b"file\0"
        ),
    )

    with pytest.raises(ValueError, match="dirty_content_unsafe_path:file"):
        change_provenance.dirty_content_sha256(linked_root)


def test_dirty_content_digest_rejects_path_replacement_after_read(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "file"
    target.write_bytes(b"content")
    outside = tmp_path / "outside"
    outside.write_bytes(b"outside")
    monkeypatch.setattr(
        change_provenance,
        "run_git",
        lambda _root, *args, **_kwargs: SimpleNamespace(
            stdout=b"" if args[0] == "diff" else b"file\0"
        ),
    )
    original_fstat = change_provenance.os.fstat
    regular_fstat_calls = 0

    def replace_after_read(descriptor: int):
        nonlocal regular_fstat_calls
        observed = original_fstat(descriptor)
        if stat.S_ISREG(observed.st_mode):
            regular_fstat_calls += 1
            if regular_fstat_calls == 2:
                target.unlink()
                target.symlink_to(outside)
        return observed

    monkeypatch.setattr(change_provenance.os, "fstat", replace_after_read)

    with pytest.raises(ValueError, match="dirty_content_unstable_path:file"):
        change_provenance.dirty_content_sha256(tmp_path)


def test_dirty_content_digest_opens_special_files_nonblocking(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fifo = tmp_path / "fifo"
    os.mkfifo(fifo)
    monkeypatch.setattr(
        change_provenance,
        "run_git",
        lambda _root, *args, **_kwargs: SimpleNamespace(
            stdout=b"" if args[0] == "diff" else b"fifo\0"
        ),
    )
    original_open = change_provenance.os.open

    def guarded_open(path, flags, *args, **kwargs):
        if path == "fifo":
            assert flags & os.O_NONBLOCK
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(change_provenance.os, "open", guarded_open)

    with pytest.raises(ValueError, match="dirty_content_unsafe_path:fifo"):
        change_provenance.dirty_content_sha256(tmp_path)
