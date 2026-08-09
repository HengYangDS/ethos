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
from tests.support.literal_cases import literal_case

_HANDOFF = {
    "source_lane_ref": "work/example",
    "source_head": "a" * 40,
    "source_tree": "b" * 40,
    "base_commitment_path": "openspec/changes/example/commitment.toml",
    "base_commitment_bytes_sha256": "1" * 64,
    "target_holder_ref": HolderRef.parse("agent:other:run:two"),
    "context_digest": "c" * 64,
    "dirty_content_sha256": "f" * 64,
    "source_lane_incarnation_id": "lane-incarnation:one",
    "source_lease_id": "lease:one",
    "source_lease_epoch": 3,
    "source_lease_expires_at": "2026-07-20T00:00:00+00:00",
    "source_lease_payload_sha256": "e" * 64,
    "base_commitment_digest": "f" * 64,
    "source_holder_ref": HolderRef.parse("agent:source:run:one"),
}


def _handoff(**overrides: object) -> CrossHostHandoff:
    return CrossHostHandoff(**(_HANDOFF | overrides))


def _mock_dirty_git(monkeypatch: pytest.MonkeyPatch, selected: bytes) -> None:
    def run_git(_root, *args, **_kwargs):
        return SimpleNamespace(stdout=b"" if args[0] == "diff" else selected)

    monkeypatch.setattr(change_provenance, "run_git", run_git)


@pytest.mark.parametrize("width", [40, 64])
def test_cross_host_handoff_transfers_content_not_source_lease(width: int) -> None:
    payload = _handoff(
        source_head="a" * width,
        source_tree="b" * width,
        artifacts=({"path": "repository.bundle", "sha256": "d" * 64, "kind": "git_bundle"},),
    ).to_payload()
    expected = {
        "source_head": "a" * width,
        "source_tree": "b" * width,
        "base_commitment_path": "openspec/changes/example/commitment.toml",
        "base_commitment_bytes_sha256": "1" * 64,
        "target_holder_ref": "agent:other:run:two",
        "dirty_content_sha256": "f" * 64,
        "base_commitment_digest": "f" * 64,
        "transfers_source_lease": False,
        "destination_creates_local_incarnation": True,
        "truth_boundary": "content_addressed_context_until_promoted",
    }
    assert expected.items() <= payload.items()
    lease = payload["source_lease_binding"]
    keys = "lane_incarnation_id", "epoch", "expires_at", "payload_sha256"
    assert [lease[key] for key in keys] == [
        "lane-incarnation:one",
        3,
        "2026-07-20T00:00:00+00:00",
        "e" * 64,
    ]
    assert all(
        CrossHostHandoff.model_fields[field].is_required()
        for field in (
            "source_lease_expires_at",
            "source_lane_incarnation_id",
            "source_lease_payload_sha256",
            "base_commitment_path",
            "base_commitment_bytes_sha256",
            "base_commitment_digest",
        )
    )


def _artifact(**overrides: str) -> tuple[dict[str, str]]:
    return ({"path": "repository.bundle", "sha256": "d" * 64, "kind": "git_bundle"} | overrides,)


_VALIDATION_CASES = literal_case("kernel.test_handoff_contract:assign:_VALIDATION_CASES:derived")


@pytest.mark.parametrize(("absent", "overrides"), _VALIDATION_CASES)
def test_cross_host_handoff_validation_matrix(absent: str, overrides: dict[str, object]) -> None:
    payload = _HANDOFF | overrides
    if absent:
        del payload[absent]
    with pytest.raises(ValidationError):
        CrossHostHandoff(**payload)


def test_handoff_export_rejects_a_bundle_from_another_generation(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def run_git(_root, *args, **_kwargs):
        head = f"{'f' * 40} refs/heads/work/example\n"
        return SimpleNamespace(stdout=head if args[:2] == ("bundle", "list-heads") else "")

    patches = {
        "run_git": run_git,
        "_artifact": lambda path, _root, kind: {
            "path": path.name,
            "sha256": "0" * 64,
            "kind": kind,
        },
    }
    for name, replacement in patches.items():
        monkeypatch.setattr(handoff_package, name, replacement)

    def noop(*_args, **_kwargs):
        return None

    for name in ("_require_schema", "_verify_export_snapshot", "_publish_package"):
        monkeypatch.setattr(handoff_package, name, noop)
    with pytest.raises(ValueError, match="handoff_bundle_identity_mismatch"):
        handoff_package.write_handoff_package(
            repo=tmp_path,
            handoff=_handoff(
                dirty_content_sha256="d" * 64,
                source_lease_epoch=1,
                source_lease_expires_at="2026-07-21T00:00:00+00:00",
            ),
            context="context",
            output_root=tmp_path / "output",
        )


def test_handoff_manifest_rejects_a_symlinked_manifest(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (package := tmp_path / "handoff:package").mkdir()
    (outside := tmp_path / "outside.json").write_text("{}\n", encoding="utf-8")
    (package / "manifest.json").symlink_to(outside)

    def valid(*_args, **_kwargs):
        return {"verdict": "pass", "required_gaps": []}

    monkeypatch.setattr(handoff_package, "validate_schema_instance", valid)
    _, gaps = handoff_package.verified_handoff_manifest(package=package, root=tmp_path)
    assert gaps == ["handoff_manifest_unsafe"]


@pytest.mark.parametrize(
    ("state", "gap"),
    literal_case(
        "kernel.test_handoff_contract:parametrize:test_handoff_import_rejects_destination_lease_before_git_effects:0"
    ),
)
def test_handoff_import_rejects_destination_lease_before_git_effects(
    tmp_path, monkeypatch: pytest.MonkeyPatch, state: str, gap: str
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

    with pytest.raises(ValueError, match=rf"^{gap}$"):
        destination_import.apply_handoff_import(
            destination=destination,
            package=tmp_path / "package",
            manifest={
                "package_id": f"handoff:{'c' * 64}",
                "source_lane_ref": branch,
                "source_head": "a" * 40,
                "source_tree": "d" * 40,
                "base_commitment_path": "openspec/changes/example/commitment.toml",
                "base_commitment_bytes_sha256": "e" * 64,
                "base_commitment_digest": "b" * 64,
            },
            target_holder_ref="agent:test:case:target",
        )

    assert git_calls == []


def test_dirty_content_digest_frames_path_and_content(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name, content in (("a", b"bc"), ("ab", b"c")):
        (tmp_path / name).write_bytes(content)
    selected = [b"a\0"]

    def run_git(_root, *args, **kwargs):
        assert kwargs["text"] is False
        return SimpleNamespace(stdout=b"" if args[0] == "diff" else selected[0])

    monkeypatch.setattr(change_provenance, "run_git", run_git)
    first = change_provenance.dirty_content_sha256(tmp_path)
    selected[0] = b"ab\0"
    assert change_provenance.dirty_content_sha256(tmp_path) != first


_DIRTY_CASES = [
    ("link", "dirty_content_unsafe_path:link"),
    *((case, "dirty_content_snapshot_drift") for case in ("patch", "inventory")),
    ("root", "dirty_content_unsafe_path:file"),
    ("replace", "dirty_content_unstable_path:file"),
]


def _drifting_git(case: str):
    calls = {"diff": 0, "ls-files": 0}

    def run_git(_root, *args, **_kwargs):
        command = args[0]
        calls[command] += 1
        kind = {"diff": "patch", "ls-files": "inventory"}[command]
        changed = calls[command] == 2 and case == kind
        if command == "diff":
            return SimpleNamespace(stdout=b"changed" if changed else b"")
        return SimpleNamespace(stdout=b"other\0" if changed else b"file\0")

    return run_git


def _replace_on_second_regular_fstat(file, outside):
    original, calls = change_provenance.os.fstat, [0]

    def fstat(descriptor: int):
        observed = original(descriptor)
        if stat.S_ISREG(observed.st_mode):
            calls[0] += 1
            if calls[0] == 2:
                file.unlink()
                file.symlink_to(outside)
        return observed

    return fstat


@pytest.mark.parametrize(("case", "gap"), _DIRTY_CASES)
def test_dirty_content_digest_negative_matrix(
    tmp_path, monkeypatch: pytest.MonkeyPatch, case: str, gap: str
) -> None:
    target = tmp_path
    if case == "link":
        (outside := tmp_path.parent / "outside").write_bytes(b"external")
        (tmp_path / "link").symlink_to(outside)
        _mock_dirty_git(monkeypatch, b"link\0")
    elif case in {"patch", "inventory"}:
        (tmp_path / "file").write_bytes(b"content")
        monkeypatch.setattr(change_provenance, "run_git", _drifting_git(case))
    elif case == "root":
        target = tmp_path / "linked"
        (real := tmp_path / "real").mkdir()
        (real / "file").write_bytes(b"content")
        target.symlink_to(real, target_is_directory=True)
        _mock_dirty_git(monkeypatch, b"file\0")
    else:
        for name, content in (("file", b"content"), ("outside", b"outside")):
            (tmp_path / name).write_bytes(content)
        file, outside = tmp_path / "file", tmp_path / "outside"
        _mock_dirty_git(monkeypatch, b"file\0")
        monkeypatch.setattr(
            change_provenance.os, "fstat", _replace_on_second_regular_fstat(file, outside)
        )
    with pytest.raises(ValueError, match=gap):
        change_provenance.dirty_content_sha256(target)


def test_dirty_content_digest_opens_special_files_nonblocking(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    os.mkfifo(tmp_path / "fifo")
    _mock_dirty_git(monkeypatch, b"fifo\0")
    original = change_provenance.os.open

    def open_(path, flags, *args, **kwargs):
        assert path != "fifo" or flags & os.O_NONBLOCK
        return original(path, flags, *args, **kwargs)

    monkeypatch.setattr(change_provenance.os, "open", open_)
    with pytest.raises(ValueError, match="dirty_content_unsafe_path:fifo"):
        change_provenance.dirty_content_sha256(tmp_path)
