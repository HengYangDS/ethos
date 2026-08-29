from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.lane_lifecycle.handoff.transfer as transfer
from ethos.contracts.coordination import CrossHostHandoffExportRequest
from ethos.contracts.coordination import CrossHostHandoffImportRequest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("text", "file_content", "gap"),
    [
        ("inline", "file", "handoff_context_ambiguous"),
        ("", "", "handoff_context_required"),
        ("", None, "handoff_context_file_unreadable"),
    ],
)
def test_handoff_context_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    text: str,
    file_content: str | None,
    gap: str,
) -> None:
    context_file = tmp_path / "context.md"
    if file_content is not None:
        context_file.write_text(file_content, encoding="utf-8")

    request = _export_request(
        tmp_path,
        root=tmp_path.as_posix(),
        context_text=text,
        context_file=context_file.as_posix(),
    )
    _mock_export_observations(monkeypatch, tmp_path)

    report = transfer.export_cross_host_handoff(request)

    assert gap in report["required_gaps"]


@pytest.mark.parametrize(
    ("lease", "gap"),
    [
        ({"lease_state": "unknown"}, "work_lane_lease_unknown:work/example"),
        ({"lease_state": "expired"}, "work_lane_lease_expired:work/example"),
        ({}, "work_lane_missing_lease:work/example"),
    ],
)
def test_lease_state_gap_is_actionable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    lease: dict[str, object],
    gap: str,
) -> None:
    _mock_export_observations(monkeypatch, tmp_path, lease=lease)

    report = transfer.export_cross_host_handoff(_export_request(tmp_path))

    assert gap in report["required_gaps"]


def test_import_reports_invalid_holder_before_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = tmp_path / "package"
    package.mkdir()
    monkeypatch.setattr(transfer, "repository_root", lambda _root: tmp_path)
    monkeypatch.setattr(
        transfer,
        "workspace_status",
        lambda _root: {"role": "accepted_root", "dirty": False},
    )
    monkeypatch.setattr(
        transfer.handoff_package,
        "verified_handoff_manifest",
        lambda **_kwargs: (
            {
                "package_id": "handoff:1",
                "source_lane_ref": "work/example",
                "source_head": "a" * 40,
                "source_tree": "b" * 40,
                "target_holder_ref": "agent:test:case:target",
            },
            [],
        ),
    )
    monkeypatch.setattr(
        transfer,
        "apply_handoff_import",
        lambda **_kwargs: pytest.fail("effect must not run"),
    )

    report = transfer.import_cross_host_handoff(
        CrossHostHandoffImportRequest(
            root=tmp_path.as_posix(),
            package=package.as_posix(),
            target_holder_ref="invalid",
            apply=True,
        )
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == [
        "target_holder_ref_invalid",
        "handoff_target_holder_mismatch",
        "handoff_target_actor_mismatch",
    ]


def test_import_wraps_effect_failure_in_public_gap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    holder = "agent:test:case:target"
    package = tmp_path / "package"
    package.mkdir()
    monkeypatch.setenv("ETHOS_ACTOR", holder)
    monkeypatch.setattr(transfer, "repository_root", lambda _root: tmp_path)
    monkeypatch.setattr(
        transfer,
        "workspace_status",
        lambda _root: {"role": "accepted_root", "dirty": False},
    )
    monkeypatch.setattr(
        transfer.handoff_package,
        "verified_handoff_manifest",
        lambda **_kwargs: (
            {
                "package_id": "handoff:1",
                "source_lane_ref": "work/example",
                "source_head": "a" * 40,
                "source_tree": "b" * 40,
                "target_holder_ref": holder,
            },
            [],
        ),
    )

    def fail_import(**_kwargs):
        message = "destination_cas_stale"
        raise ValueError(message)

    monkeypatch.setattr(transfer, "apply_handoff_import", fail_import)

    report = transfer.import_cross_host_handoff(
        CrossHostHandoffImportRequest(
            root=tmp_path.as_posix(),
            package=package.as_posix(),
            target_holder_ref=holder,
            apply=True,
        )
    )

    assert report["verdict"] == "block"
    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["handoff_import_failed:destination_cas_stale"]
    assert report["mutation"]["decision"]["verdict"] == "block"


def test_export_reports_each_invalid_holder_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _mock_export_observations(monkeypatch, tmp_path)

    report = transfer.export_cross_host_handoff(
        _export_request(tmp_path, holder_ref="invalid", target_holder_ref="also-invalid")
    )

    assert "holder_ref_invalid" in report["required_gaps"]
    assert "target_holder_ref_invalid" in report["required_gaps"]


def _export_request(tmp_path: Path, **overrides: object) -> CrossHostHandoffExportRequest:
    values: dict[str, object] = {
        "root": tmp_path.as_posix(),
        "branch": "work/example",
        "holder_ref": "agent:test:case:source",
        "target_holder_ref": "agent:test:case:target",
        "generation": 1,
        "expires_at": "2026-08-29T12:00:00+00:00",
        "expect_head": "b" * 40,
        "context_text": "context",
        "context_file": None,
        "apply": False,
    }
    return CrossHostHandoffExportRequest(**(values | overrides))


def _mock_export_observations(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    lease: dict[str, object] | None = None,
) -> None:
    observed_lease = {
        "lease_state": "valid",
        "holder_ref": "agent:test:case:source",
        "generation": 1,
        "expires_at": "2026-08-29T12:00:00+00:00",
    }
    if lease is not None:
        observed_lease = lease
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:source")
    monkeypatch.setattr(transfer, "repository_root", lambda _root: tmp_path)
    monkeypatch.setattr(
        transfer,
        "workspace_status",
        lambda _root: {"role": "work_lane", "branch": "work/example"},
    )
    monkeypatch.setattr(
        transfer,
        "run_git",
        lambda _root, *args: type(
            "Result",
            (),
            {"stdout": "b" * 40 if args[-1] == "HEAD" else "c" * 40},
        )(),
    )
    monkeypatch.setattr(
        transfer, "leases_by_branch", lambda _root: {"work/example": observed_lease}
    )
    monkeypatch.setattr(transfer, "changed_paths", lambda _root: ())
    monkeypatch.setattr(transfer.handoff_package, "dirty_content_sha256", lambda _root: "f" * 64)
