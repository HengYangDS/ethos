from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from ethos.adapters.mutation.lane_lifecycle.handoff import package as handoff_package
from ethos_core.contracts.coordination import CrossHostHandoff
from ethos_core.contracts.coordination import HolderRef


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
        source_holder_ref=HolderRef.parse("agent:source:run:one"),
        artifacts=({"path": "repository.bundle", "sha256": "d" * 64, "kind": "git_bundle"},),
    )

    payload = handoff.to_payload()
    assert payload["source_head"] == "a" * width
    assert payload["source_tree"] == "b" * width
    assert payload["target_holder_ref"] == "agent:other:run:two"
    assert payload["dirty_content_sha256"] == "f" * 64
    assert payload["transfers_source_lease"] is False
    assert payload["destination_creates_local_incarnation"] is True
    assert payload["source_lease_binding"]["epoch"] == 3
    assert payload["source_lease_binding"]["expires_at"] == "2026-07-20T00:00:00+00:00"
    assert payload["source_lease_binding"]["payload_sha256"] == "e" * 64
    assert payload["truth_boundary"] == "content_addressed_context_until_promoted"
    assert CrossHostHandoff.model_fields["source_lease_expires_at"].is_required()
    assert CrossHostHandoff.model_fields["source_lease_payload_sha256"].is_required()


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


def test_dirty_content_digest_frames_path_and_content(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "a").write_bytes(b"bc")
    (tmp_path / "ab").write_bytes(b"c")
    monkeypatch.setattr(
        handoff_package,
        "run_git",
        lambda *_args, **_kwargs: SimpleNamespace(stdout=""),
    )
    monkeypatch.setattr(handoff_package, "_git_lines", lambda *_args: ["a"])
    first = handoff_package.dirty_content_sha256(tmp_path)
    monkeypatch.setattr(handoff_package, "_git_lines", lambda *_args: ["ab"])

    assert handoff_package.dirty_content_sha256(tmp_path) != first
