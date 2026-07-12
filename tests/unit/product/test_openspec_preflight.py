from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.openspec.preflight.core import openspec_archive_preflight_report

if TYPE_CHECKING:
    from pathlib import Path


def _result(**kwargs: object) -> dict[str, object]:
    return {
        "command": ["openspec", "archive"],
        "exit_code": 0,
        "stdout": "{}",
        "stderr": "",
        "json": {"archive": {"change": "sample-change"}, "status": []},
        "parse_error": "",
    } | kwargs


@pytest.mark.parametrize(
    ("case", "code"),
    [
        ("ready", ""),
        ("redacted", "archive_spec_update_failed"),
        ("invalid-json", "official_archive_json_parse_failed"),
        ("timeout", "openspec_command_timeout"),
        ("receipt", "official_archive_result_invalid"),
        ("copy", "workspace_copy_failed"),
        ("invoke", "official_archive_invocation_failed"),
    ],
)
def test_official_archive_preflight_isolated_and_fail_closed(
    tmp_path: Path, monkeypatch, case: str, code: str
) -> None:
    root = tmp_path / "repo"
    tracked = root / "openspec" / "specs" / "adapters" / "spec.md"
    tracked.parent.mkdir(parents=True)
    tracked.write_text("# Adapters\n", encoding="utf-8")
    before = tracked.read_text(encoding="utf-8")
    roots: list[Path] = []
    if case == "copy":
        monkeypatch.setattr(
            shutil, "copytree", lambda *_args: (_ for _ in ()).throw(shutil.Error())
        )

    def run(command_root: Path, _base: tuple[str, ...], args: tuple[str, ...]) -> dict[str, object]:
        roots.append(command_root)
        assert args == ("archive", "sample-change", "--yes", "--json")
        if case == "ready":
            assert (command_root / "openspec" / "specs" / "adapters" / "spec.md").read_text(
                encoding="utf-8"
            ) == before
        if case == "invoke":
            raise OSError(case)
        if case == "redacted":
            return _result(
                exit_code=1,
                json={
                    "archive": None,
                    "status": [
                        {
                            "severity": "error",
                            "code": code,
                            "message": str(command_root),
                        }
                    ],
                },
            )
        return {
            "invalid-json": _result(json={}, parse_error="invalid"),
            "timeout": _result(exit_code=124, json={}, parse_error="openspec_command_timeout"),
            "receipt": _result(json={"archive": None, "status": []}),
        }.get(case, _result())

    report = openspec_archive_preflight_report(
        root, "sample-change", base_command=("openspec",), run_json=run
    )

    assert report["state"] == ("ready" if not code else "blocked")
    assert tracked.read_text(encoding="utf-8") == before
    if code:
        assert report["required_gaps"] == [
            f"openspec_archive_preflight_failed:sample-change:{code}"
        ]
        if case == "copy":
            assert tmp_path.as_posix() not in str(report)
    else:
        assert roots
        assert roots[0] != root
    if case == "redacted":
        assert roots[0].as_posix() not in str(report)
    if case == "invoke":
        assert case not in str(report)
