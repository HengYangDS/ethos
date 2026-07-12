from __future__ import annotations

import shutil
from pathlib import Path

from ethos.adapters.openspec.preflight.core import openspec_archive_preflight_report


def test_official_archive_preflight_is_ready_without_mutating_source(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    source = root / "openspec"
    source.mkdir(parents=True)
    tracked = source / "specs" / "adapters" / "spec.md"
    tracked.parent.mkdir(parents=True)
    tracked.write_text("# Adapters\n", encoding="utf-8")
    before = tracked.read_text(encoding="utf-8")
    roots: list[Path] = []

    def fake_run_json(
        command_root: Path,
        _base: tuple[str, ...],
        args: tuple[str, ...],
    ) -> dict[str, object]:
        roots.append(command_root)
        assert args == ("archive", "sample-change", "--yes", "--json")
        assert command_root != root
        assert (command_root / "openspec" / "specs" / "adapters" / "spec.md").read_text(
            encoding="utf-8"
        ) == before
        return {
            "command": ["openspec", *args],
            "exit_code": 0,
            "stdout": "{}",
            "stderr": "",
            "json": {"archive": {"change": "sample-change"}},
            "parse_error": "",
        }

    report = openspec_archive_preflight_report(
        root,
        "sample-change",
        base_command=("openspec",),
        run_json=fake_run_json,
    )

    assert roots
    assert report["ok"] is True
    assert report["state"] == "ready"
    assert report["required_gaps"] == []
    assert tracked.read_text(encoding="utf-8") == before


def test_official_archive_preflight_redacts_isolated_root_from_diagnostics(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    (root / "openspec").mkdir(parents=True)
    command_roots: list[Path] = []

    def fake_run_json(
        command_root: Path,
        _base: tuple[str, ...],
        _args: tuple[str, ...],
    ) -> dict[str, object]:
        command_roots.append(command_root)
        return {
            "command": ["openspec", "archive"],
            "exit_code": 1,
            "stdout": "{}",
            "stderr": "",
            "json": {
                "archive": None,
                "status": [
                    {
                        "severity": "error",
                        "code": "archive_spec_update_failed",
                        "message": f"{command_root}/openspec/specs/adapters/spec.md already exists",
                        "fix": f"Remove {command_root}/openspec/specs/adapters/spec.md.",
                    }
                ],
            },
            "parse_error": "",
        }

    report = openspec_archive_preflight_report(
        root,
        "sample-change",
        base_command=("openspec",),
        run_json=fake_run_json,
    )

    assert command_roots
    assert command_roots[0].as_posix() not in str(report)
    assert report["diagnostics"] == [
        {
            "severity": "error",
            "code": "archive_spec_update_failed",
            "message": "<isolated-openspec-root>/openspec/specs/adapters/spec.md already exists",
            "fix": "Remove <isolated-openspec-root>/openspec/specs/adapters/spec.md.",
        }
    ]


def test_official_archive_preflight_uses_stable_gap_for_invalid_json(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    (root / "openspec").mkdir(parents=True)

    def fake_run_json(
        _command_root: Path,
        _base: tuple[str, ...],
        _args: tuple[str, ...],
    ) -> dict[str, object]:
        return {
            "command": ["openspec", "archive"],
            "exit_code": 0,
            "stdout": "not json",
            "stderr": "",
            "json": {},
            "parse_error": "Expecting value: line 1 column 1 (char 0)",
        }

    report = openspec_archive_preflight_report(
        root,
        "sample-change",
        base_command=("openspec",),
        run_json=fake_run_json,
    )

    assert report["required_gaps"] == [
        "openspec_archive_preflight_failed:sample-change:official_archive_json_parse_failed"
    ]


def test_official_archive_preflight_uses_timeout_gap(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "openspec").mkdir(parents=True)

    report = openspec_archive_preflight_report(
        root,
        "sample-change",
        base_command=("openspec",),
        run_json=lambda *_args: {
            "command": ["openspec", "archive"],
            "exit_code": 124,
            "stdout": "",
            "stderr": "timed out",
            "json": {},
            "parse_error": "openspec_command_timeout",
        },
    )

    assert report["required_gaps"] == [
        "openspec_archive_preflight_failed:sample-change:openspec_command_timeout"
    ]


def test_official_archive_preflight_rejects_missing_archive_receipt(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    (root / "openspec").mkdir(parents=True)

    report = openspec_archive_preflight_report(
        root,
        "sample-change",
        base_command=("openspec",),
        run_json=lambda *_args: {
            "command": ["openspec", "archive"],
            "exit_code": 0,
            "stdout": "{}",
            "stderr": "",
            "json": {"archive": None},
            "parse_error": "",
        },
    )

    assert report["required_gaps"] == [
        "openspec_archive_preflight_failed:sample-change:official_archive_result_invalid"
    ]


def test_official_archive_preflight_fails_closed_when_copy_cannot_be_created(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path / "repo"
    (root / "openspec").mkdir(parents=True)

    def fail_copytree(*_args: object, **_kwargs: object) -> None:
        raise shutil.Error("copy denied")

    monkeypatch.setattr(shutil, "copytree", fail_copytree)

    report = openspec_archive_preflight_report(
        root,
        "sample-change",
        base_command=("openspec",),
        run_json=lambda *_args: {},
    )

    assert report["state"] == "blocked"
    assert report["diagnostics"] == [
        {
            "severity": "error",
            "code": "workspace_copy_failed",
            "message": "OpenSpec workspace copy failed.",
        }
    ]
    assert report["required_gaps"] == [
        "openspec_archive_preflight_failed:sample-change:workspace_copy_failed"
    ]
    assert tmp_path.as_posix() not in str(report)


def test_official_archive_preflight_fails_closed_when_official_command_cannot_start(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    (root / "openspec").mkdir(parents=True)

    def fail_run_json(
        _command_root: Path,
        _base: tuple[str, ...],
        _args: tuple[str, ...],
    ) -> dict[str, object]:
        raise OSError("private runner failure")

    report = openspec_archive_preflight_report(
        root,
        "sample-change",
        base_command=("openspec",),
        run_json=fail_run_json,
    )

    assert report["diagnostics"] == [
        {
            "severity": "error",
            "code": "official_archive_invocation_failed",
            "message": "Official OpenSpec archive command could not start.",
        }
    ]
    assert report["required_gaps"] == [
        "openspec_archive_preflight_failed:sample-change:official_archive_invocation_failed"
    ]
    assert "private runner failure" not in str(report)
