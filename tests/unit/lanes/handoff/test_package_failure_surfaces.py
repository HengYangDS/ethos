from __future__ import annotations

import json
import os
import sqlite3
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.lane_lifecycle.handoff.package as handoff_package
from ethos.contracts.coordination import CrossHostHandoff
from ethos.contracts.coordination import HolderRef

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("content", "gap"),
    [("{", "handoff_manifest_invalid_json"), ("[]", "handoff_manifest_invalid")],
)
def test_manifest_rejects_invalid_json_shapes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    content: str,
    gap: str,
) -> None:
    package = tmp_path / "handoff:invalid"
    package.mkdir()
    (package / "manifest.json").write_text(content, encoding="utf-8")
    monkeypatch.setattr(
        handoff_package,
        "validate_schema_instance",
        lambda *_args, **_kwargs: {"required_gaps": []},
    )

    manifest, gaps = handoff_package.verified_handoff_manifest(package=package, root=tmp_path)

    assert manifest == {}
    assert gaps == [gap]


@pytest.mark.parametrize("failure", ["missing", "digest"])
def test_manifest_rejects_missing_or_tampered_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    package = tmp_path / "handoff:package"
    package.mkdir()
    context = package / "context.md"
    context.write_text("context\n", encoding="utf-8")
    bundle = package / "repository.bundle"
    if failure == "digest":
        bundle.write_bytes(b"tampered")
    manifest = {
        "package_id": package.name,
        "artifacts": [
            {"path": "repository.bundle", "kind": "git_bundle", "sha256": "0" * 64},
            {
                "path": "context.md",
                "kind": "context",
                "sha256": handoff_package.hashlib.sha256(context.read_bytes()).hexdigest(),
            },
        ],
    }
    (package / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(
        handoff_package,
        "validate_schema_instance",
        lambda *_args, **_kwargs: {"required_gaps": []},
    )
    monkeypatch.setattr(handoff_package, "_content_id", lambda *_args, **_kwargs: package.name)

    _manifest, gaps = handoff_package.verified_handoff_manifest(package=package, root=tmp_path)

    expected = (
        "handoff_artifact_missing:repository.bundle"
        if failure == "missing"
        else "handoff_artifact_digest_mismatch:repository.bundle"
    )
    assert expected in gaps


def test_export_snapshot_collapses_lease_cas_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = tmp_path / "state.sqlite"
    sqlite3.connect(database).close()
    handoff = CrossHostHandoff(
        source_lane_ref="work/example",
        source_head="a" * 40,
        source_tree="e" * 40,
        source_holder_ref=HolderRef.parse("agent:test:case:source"),
        target_holder_ref=HolderRef.parse("agent:test:case:target"),
        dirty_content_sha256="c" * 64,
        source_lease_generation=1,
        source_lease_expires_at="2026-08-10T00:00:00+00:00",
        context_digest="9" * 64,
    )
    monkeypatch.setattr(
        handoff_package,
        "run_git",
        lambda *_args, **_kwargs: SimpleNamespace(stdout=handoff.source_head),
    )
    monkeypatch.setattr(
        handoff_package, "dirty_content_sha256", lambda _repo: handoff.dirty_content_sha256
    )
    monkeypatch.setattr(handoff_package, "state_database", lambda _repo: database)
    monkeypatch.setattr(handoff_package, "lease_binding", lambda *_args: object())

    def reject_lease(*_args, **_kwargs):
        message = "lease_generation_stale"
        raise ValueError(message)

    monkeypatch.setattr(handoff_package, "expected_current_lease", reject_lease)

    with pytest.raises(ValueError, match=r"^handoff_export_lease_drift$"):
        handoff_package.write_handoff_package(
            repo=tmp_path,
            handoff=handoff,
            context="context",
            output_root=tmp_path / "packages",
        )


def test_package_snapshot_rejects_non_regular_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = tmp_path / "handoff:package"
    package.mkdir()
    os.mkfifo(package / "artifact")
    monkeypatch.setattr(
        handoff_package,
        "verified_handoff_manifest",
        lambda **_kwargs: ({"package_id": package.name}, []),
    )

    with (
        pytest.raises(ValueError, match=r"^handoff_artifact_unsafe:artifact$"),
        handoff_package.verified_package_snapshot(
            package=package,
            manifest={"package_id": package.name},
            root=tmp_path,
        ),
    ):
        pass
