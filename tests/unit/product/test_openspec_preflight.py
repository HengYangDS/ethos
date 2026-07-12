from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.openspec.preflight.core as preflight_core
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


def _configure_case(root: Path, tmp_path: Path, case: str, monkeypatch) -> None:
    if case == "missing":
        shutil.rmtree(root / "openspec")
    elif case == "copy":
        monkeypatch.setattr(
            shutil, "copytree", lambda *_args: (_ for _ in ()).throw(shutil.Error())
        )
    elif case == "temporary":
        monkeypatch.setattr(
            preflight_core, "TemporaryDirectory", lambda **_kwargs: (_ for _ in ()).throw(OSError())
        )
    elif case == "cleanup":

        class BrokenTemporary:
            name = str(tmp_path / "broken-temporary")

            def __init__(self, **_kwargs: object) -> None:
                pass

            def cleanup(self) -> None:
                raise OSError

        monkeypatch.setattr(preflight_core, "TemporaryDirectory", BrokenTemporary)


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
        ("missing", "workspace_missing"),
        ("temporary", "isolated_workspace_unavailable"),
        ("cleanup", "isolated_workspace_cleanup_failed"),
        ("none", "official_archive_invocation_failed"),
        ("exit", "official_archive_failed"),
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
    _configure_case(root, tmp_path, case, monkeypatch)

    def run(command_root: Path, _base: tuple[str, ...], args: tuple[str, ...]) -> dict[str, object]:
        roots.append(command_root)
        assert args == ("archive", "sample-change", "--yes", "--json")
        if case == "ready":
            assert (command_root / "openspec" / "specs" / "adapters" / "spec.md").read_text(
                encoding="utf-8"
            ) == before
        if case == "invoke":
            raise OSError(case)
        if case == "none":
            return None  # type: ignore[return-value]
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
            "invalid-json": _result(json=[], parse_error="invalid"),
            "timeout": _result(exit_code=124, json={}, parse_error="openspec_command_timeout"),
            "receipt": _result(json={"archive": None, "status": [None]}),
            "exit": _result(exit_code="failed", json={}),
        }.get(case, _result())

    report = openspec_archive_preflight_report(
        root, "sample-change", base_command=("openspec",), run_json=run
    )

    assert report["state"] == ("ready" if not code else "blocked")
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
