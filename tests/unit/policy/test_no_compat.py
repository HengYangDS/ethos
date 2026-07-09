from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.policy.no_compat.core import no_compat_report

if TYPE_CHECKING:
    from pathlib import Path


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_no_compat_report_blocks_production_residue(tmp_path: Path) -> None:
    _write(
        tmp_path / "packages/ethos/src/ethos/sample/core.py",
        "def legacy_wrapper():\n    return 1\n",
    )

    report = no_compat_report(tmp_path)

    assert report["ok"] is False
    assert report["required_gaps"] == [
        "no_compat_residue:forbidden_identifier:"
        "packages/ethos/src/ethos/sample/core.py:1:legacy_wrapper"
    ]


def test_no_compat_report_ignores_tests_and_its_own_policy_names(tmp_path: Path) -> None:
    _write(
        tmp_path / "tests/unit/sample/test_legacy.py",
        "def test_legacy_fixture():\n    assert True\n",
    )
    _write(
        tmp_path / "packages/ethos/src/ethos/repository/policy/no_compat/core.py",
        "def no_compat_report():\n    return {}\n",
    )
    _write(
        tmp_path / "packages/ethos/src/ethos/sample/core.py",
        "def current_surface():\n    return 1\n",
    )

    report = no_compat_report(tmp_path)

    assert report["ok"] is True
    assert report["required_gaps"] == []


def test_no_compat_report_blocks_dynamic_module_export(tmp_path: Path) -> None:
    _write(
        tmp_path / "packages/ethos/src/ethos/sample/core.py",
        "def __getattr__(name):\n    raise AttributeError(name)\n",
    )

    report = no_compat_report(tmp_path)

    assert report["required_gaps"] == [
        "no_compat_residue:dynamic_export:packages/ethos/src/ethos/sample/core.py:"
        "1:module_getattr_forwarding_surface"
    ]


def test_no_compat_report_blocks_compatibility_shell_paths(tmp_path: Path) -> None:
    _write(
        tmp_path / "packages/ethos/src/ethos/sample/compat.py",
        "def current_surface():\n    return 1\n",
    )

    report = no_compat_report(tmp_path)

    assert report["required_gaps"] == [
        "no_compat_residue:forbidden_path_part:packages/ethos/src/ethos/sample/compat.py:1:compat"
    ]
