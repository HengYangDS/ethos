from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import ethos.surface.cli.lane.lifecycle as lifecycle


def _capture(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    results: list[Any] = []
    monkeypatch.setattr(lifecycle, "emit", lambda result, **_kwargs: results.append(result))
    return results


@pytest.mark.parametrize(
    ("command", "report", "state", "action"),
    [
        (
            "lane status",
            {"verdict": "pass", "role": "work_lane"},
            "ready",
            "ethos lane prewrite <path>",
        ),
        (
            "lane status",
            {"verdict": "block", "role": "accepted_root"},
            "blocked",
            "ethos status --json",
        ),
        (
            "lane status",
            {"verdict": "unknown", "role": "work_lane"},
            "unknown",
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
            {"verdict": "pass", "runner_bootstrap": {}},
            "ready",
            "ethos lane prewrite <path>",
        ),
        (
            "lane refresh-base",
            {"verdict": "pass", "state": "refreshed"},
            "refreshed",
            "ethos land --json",
        ),
        (
            "lane refresh-base",
            {"verdict": "block", "next_action": "resolve conflict"},
            "blocked",
            "resolve conflict",
        ),
        (
            "lane rebind-commitment",
            {"verdict": "pass", "next_action": "continue"},
            "ready",
            "continue",
        ),
        (
            "lane retire landed",
            {"verdict": "block", "required_gaps": ["lease_stale"]},
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
    assert result.required_gaps == tuple(report.get("required_gaps", ()))
    assert result.next_action == action
    assert result.to_dict()["data"] == report


def test_public_projection_accepts_explicit_and_computed_actions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    results = _capture(monkeypatch)
    report = {"verdict": "pass", "state": "planned"}

    lifecycle.project_lane_result(
        "lane custom", report, actions="apply exact plan", json_output=True
    )
    lifecycle.project_lane_result(
        "lane custom",
        report,
        actions=lambda _report, verdict: f"verdict={verdict}",
        json_output=True,
    )

    assert [result.next_action for result in results] == ["apply exact plan", "verdict=pass"]


def test_public_lifecycle_commands_forward_exact_reports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
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
    lifecycle.start(
        "example",
        SimpleNamespace(
            root=tmp_path,
            source_root=None,
            commitment=None,
            path=None,
            holder_ref="agent:test:case:owner",
            apply=True,
            command="lane start",
            json_output=True,
        ),
    )
    lifecycle.lane_refresh_base(
        SimpleNamespace(
            root=tmp_path,
            apply=True,
            authorize=True,
            expect_head="a" * 40,
            command="lane refresh-base",
            json_output=True,
        )
    )
    lifecycle.lane_archive_change(
        SimpleNamespace(
            root=tmp_path,
            change="example",
            expect_head="a" * 40,
            apply=True,
            command="lane archive-change",
            json_output=True,
        )
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
    assert captured["report"]["path_count"] == 2
