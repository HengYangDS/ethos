"""Public lifecycle projections preserve native command inputs and boundary reports."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import ethos.adapters.mutation.lane_lifecycle.archive.command as archive
import ethos.adapters.mutation.lane_lifecycle.change_overlay as overlay
import ethos.surface.cli.lane.commit_signer as commit_signer
import ethos.surface.cli.lane.lifecycle as lifecycle

ARCHIVE_BRANCH = "work/feature"
ARCHIVE_HEAD = "old-head"
ARCHIVE_CHANGE = "fixture-change"


def _capture(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    results: list[Any] = []
    monkeypatch.setattr(lifecycle, "emit", lambda result, **_kwargs: results.append(result))
    return results


@pytest.mark.parametrize(
    ("command", "report", "state", "action"),
    [
        (
            "lane status",
            {
                "verdict": "pass",
                "role": "work_lane",
                "next_action": "ethos lane prewrite <path>",
            },
            "ready",
            "ethos lane prewrite <path>",
        ),
        (
            "lane prewrite",
            {"verdict": "pass", "path_count": 1, "role": "work_lane"},
            "admitted",
            "",
        ),
        (
            "lane prewrite",
            {
                "verdict": "unknown",
                "path_count": 0,
                "role": "other",
                "required_gaps": ["editor_root_unavailable"],
                "next_action": "ethos lane prewrite <path> --editor-root <root>",
            },
            "unknown",
            "ethos lane prewrite <path> --editor-root <root>",
        ),
        (
            "lane start",
            {"verdict": "block", "required_gaps": ["lane_start_blocked"]},
            "blocked",
            "",
        ),
        (
            "lane start",
            {"verdict": "pass", "next_action": "ethos lane prewrite <path>"},
            "ready",
            "ethos lane prewrite <path>",
        ),
        (
            "lane refresh-base",
            {
                "verdict": "pass",
                "state": "refreshed",
                "next_action": "ethos land --json",
            },
            "refreshed",
            "ethos land --json",
        ),
        (
            "lane refresh-base",
            {
                "verdict": "block",
                "required_gaps": ["refresh_conflict"],
                "next_action": "resolve conflict",
            },
            "blocked",
            "resolve conflict",
        ),
        (
            "lane retire landed",
            {
                "verdict": "block",
                "required_gaps": ["lease_stale"],
                "next_action": "ethos lane status",
            },
            "blocked",
            "ethos lane status",
        ),
    ],
)
def test_public_projection_is_structured_and_actionable(
    monkeypatch: pytest.MonkeyPatch,
    command: str,
    report: dict[str, object],
    state: str,
    action: str,
) -> None:
    results = _capture(monkeypatch)

    lifecycle.project_lane_result(command, report, json_output=True)

    result = results.pop()
    assert (result.command, result.verdict, result.state) == (command, report["verdict"], state)
    expected_gaps = report.get("required_gaps", ())
    assert isinstance(expected_gaps, (list, tuple))
    assert result.required_gaps == tuple(expected_gaps)
    assert result.next_action == action
    assert result.to_dict()["data"] == report


def test_public_projection_accepts_explicit_and_computed_actions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    results = _capture(monkeypatch)
    report: dict[str, object] = {
        "verdict": "pass",
        "state": "planned",
        "next_action": "apply exact owner plan",
    }

    lifecycle.project_lane_result("lane candidate", report, json_output=True)

    assert results[0].next_action == "apply exact owner plan"


@pytest.mark.parametrize("strategy", ["rebase", "merge"])
def test_public_lifecycle_commands_forward_exact_reports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, strategy: str
) -> None:
    captured: list[tuple[str, dict[str, object], bool]] = []
    monkeypatch.setattr(lifecycle, "resolve_root", lambda _root: tmp_path)
    monkeypatch.setattr(
        lifecycle,
        "project_lane_result",
        lambda command, report, **kwargs: captured.append(
            (command, report, bool(kwargs.get("enforce")))
        ),
    )
    report = {"verdict": "pass", "state": "ready", "branch": "work/example", "path": str(tmp_path)}
    monkeypatch.setattr(
        lifecycle, "bootstrap_candidate", lambda **kwargs: report | {"call": kwargs}
    )
    monkeypatch.setattr(
        lifecycle, "refresh_candidate_from_accepted", lambda **kwargs: report | {"call": kwargs}
    )
    monkeypatch.setattr(
        lifecycle, "refresh_work_lane_base", lambda **kwargs: report | {"call": kwargs}
    )
    monkeypatch.setattr(lifecycle, "archive_change", lambda **kwargs: report | {"call": kwargs})
    monkeypatch.setattr(lifecycle, "start_work_lane", lambda **kwargs: report | {"call": kwargs})

    lifecycle.candidate(root=tmp_path, path=str(tmp_path / "candidate"))
    lifecycle.candidate(root=tmp_path, refresh_from_accepted=True, apply=True, authorize=True)

    def execute(arguments: list[str]) -> None:
        with pytest.raises(SystemExit) as exited:
            lifecycle.lane_app(arguments)
        assert exited.value.code == 0

    execute(
        [
            "start",
            "example",
            "--root",
            str(tmp_path),
            "--holder-ref",
            "agent:test:case:owner",
            "--apply",
            "--json",
        ]
    )
    arguments = [
        "refresh-base",
        "--root",
        str(tmp_path),
        "--apply",
        "--authorize",
        "--expect-head",
        "a" * 40,
        "--json",
    ]
    if strategy == "merge":
        arguments += [
            "--strategy",
            "merge",
            "--mode",
            "abort",
            "--expect-state",
            "b" * 64,
            "--subject",
            "chore: recover exact merge",
        ]
    execute(arguments)
    assert captured[-1][1]["call"] == {
        "root": tmp_path,
        "apply": True,
        "authorized": True,
        "expect_head": "a" * 40,
        "strategy": strategy,
        "mode": "abort" if strategy == "merge" else "inspect",
        "expect_state": "b" * 64 if strategy == "merge" else None,
        "subject": "chore: recover exact merge" if strategy == "merge" else None,
    }
    execute(
        [
            "archive-change",
            "--root",
            str(tmp_path),
            "--change",
            "example",
            "--expect-head",
            "a" * 40,
            "--subject",
            "chore(openspec): archive example",
            "--apply",
            "--json",
        ]
    )

    assert [item[0] for item in captured] == [
        "lane candidate",
        "lane candidate",
        "lane start",
        "lane refresh-base",
        "lane archive-change",
    ]
    assert [item[2] for item in captured] == [False, True, True, True, True]


def test_public_prewrite_command_preserves_invalid_tokens_and_patch_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setattr(lifecycle, "resolve_root", lambda _root: tmp_path)
    monkeypatch.setattr(
        lifecycle,
        "prewrite_guard",
        lambda **kwargs: captured.update(kwargs) or {"verdict": "block", "required_gaps": ["gap"]},
    )
    monkeypatch.setattr(
        lifecycle,
        "project_lane_result",
        lambda _command, report, **_kwargs: captured.update(report=report),
    )
    monkeypatch.setattr(
        lifecycle.sys, "stdin", SimpleNamespace(read=lambda: "diff --git a/a b/a\n")
    )

    lifecycle.prewrite(
        ("README.md", "bad path"),
        root=tmp_path,
        editor_root=str(tmp_path),
        require_editor_root=True,
        patch_path="-",
        json_output=True,
    )

    assert captured["paths"] == [tmp_path / "README.md", Path("bad path")]
    assert captured["editor_root"] == tmp_path
    assert captured["patch"] == "diff --git a/a b/a\n"
    report = captured["report"]
    assert isinstance(report, dict)
    assert report["path_count"] == 2


def test_commit_signer_command_forwards_exact_authority_coordinates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setattr(commit_signer, "resolve_root", lambda _root: tmp_path)
    monkeypatch.setattr(
        commit_signer,
        "authorize_configured_commit_signer",
        lambda root, revision, **kwargs: (
            captured.update(root=root, revision=revision, **kwargs)
            or {"verdict": "pass", "state": "signer_authorized"}
        ),
    )
    monkeypatch.setattr(
        commit_signer,
        "project_lane_result",
        lambda command, report, **kwargs: captured.update(
            command=command, report=report, projection=kwargs
        ),
    )
    commit_signer.trust_commit_signer(
        commit_signer.CommitSignerTrustOptions(
            target_commit="a" * 40,
            expected_anchor_sha256="b" * 64,
            authorize=True,
            apply=True,
            root=tmp_path,
            json_output=True,
        )
    )

    assert captured["root"] == tmp_path
    assert captured["revision"] == "a" * 40
    assert captured["expected_anchor_sha256"] == "b" * 64
    assert captured["authorized"] is captured["apply"] is True
    assert captured["projection"] == {"enforce": True, "json_output": True}


class _WorkLanePolicy:
    def role_for_branch(self, _branch: str) -> str:
        return "work_lane"


@pytest.mark.parametrize(
    ("lease", "actor", "expected_gap", "expected_state", "expected_action"),
    [
        (
            {},
            "agent:test",
            f"work_lane_missing_lease:{ARCHIVE_BRANCH}",
            "lease_missing",
            "ethos lane status --json",
        ),
        (
            {
                "lease_state": "expired",
                "lane_ref": ARCHIVE_BRANCH,
                "holder_ref": "agent:test",
                "generation": 7,
                "expires_at": "2026-08-20T00:00:00Z",
            },
            "agent:test",
            f"work_lane_lease_expired:{ARCHIVE_BRANCH}",
            "lease_expired",
            (
                "ethos lane lease resume --generation 7 "
                "--expires-at 2026-08-20T00:00:00Z "
                f"--branch {ARCHIVE_BRANCH} "
                "--holder-ref agent:test --apply --json"
            ),
        ),
        (
            {
                "lease_state": "valid",
                "lane_ref": ARCHIVE_BRANCH,
                "holder_ref": "agent:other",
                "generation": 1,
                "expires_at": "2026-08-30T00:00:00Z",
            },
            "agent:test",
            "lease_actor_mismatch",
            "different_holder",
            (
                "ethos attestation query --predicate lane-resolution:takeover "
                f"--subject git:branch:{ARCHIVE_BRANCH} --json"
            ),
        ),
    ],
)
def test_work_lane_transition_reports_the_first_exact_lease_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    lease: dict[str, object],
    actor: str,
    expected_gap: str,
    expected_state: str,
    expected_action: str,
) -> None:
    monkeypatch.setattr(overlay, "load_branch_role_policy", lambda _root: _WorkLanePolicy())
    monkeypatch.setattr(overlay, "git_stdout", lambda *_args: "")

    gaps = overlay.work_lane_transition_gaps(
        tmp_path,
        branch=ARCHIVE_BRANCH,
        head=ARCHIVE_HEAD,
        expect_head=ARCHIVE_HEAD,
        lease=lease,
        actor=actor,
        role_gap="archive_requires_work_lane",
    )

    assert gaps == [expected_gap]
    report = archive.archive_preflight_report(
        ARCHIVE_BRANCH, ARCHIVE_HEAD, ARCHIVE_CHANGE, gaps, lease=lease
    )
    assert report["state"] == expected_state
    assert report["next_action"] == expected_action
