from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.policy.no_compat.core import no_compat_report
from tests.support import write_text as _write

if TYPE_CHECKING:
    from pathlib import Path


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


def test_no_compat_report_skips_missing_source_roots(tmp_path: Path) -> None:
    report = no_compat_report(tmp_path)

    assert report["ok"] is True
    assert report["summary"] == {
        "finding_count": 0,
        "scanned_path_count": 0,
        "source_roots": ["packages/ethos/src", "packages/ethos-core/src"],
    }


def test_no_compat_report_reports_unparseable_python(tmp_path: Path) -> None:
    _write(
        tmp_path / "packages/ethos/src/ethos/sample/core.py",
        "def broken(:\n",
    )

    report = no_compat_report(tmp_path)

    assert report["required_gaps"] == [
        "no_compat_residue:syntax:packages/ethos/src/ethos/sample/core.py:1:unparseable_python"
    ]


def test_no_compat_report_blocks_class_assignment_and_import_residue(tmp_path: Path) -> None:
    _write(
        tmp_path / "packages/ethos/src/ethos/sample/core.py",
        """
import ethos.old as legacy_alias
from ethos.current import value as deprecated_wrapper

class CompatibilityFacade:
    pass

async def compatibility_mode():
    return None

compatibility_wrapper = 1
""".lstrip(),
    )

    report = no_compat_report(tmp_path)
    gaps = report["required_gaps"]

    assert (
        "no_compat_residue:forbidden_import:packages/ethos/src/ethos/sample/core.py:1:legacy_alias"
    ) in gaps
    assert (
        "no_compat_residue:forbidden_import:packages/ethos/src/ethos/sample/core.py:"
        "2:deprecated_wrapper"
    ) in gaps
    assert (
        "no_compat_residue:forbidden_identifier:packages/ethos/src/ethos/sample/core.py:"
        "4:compatibility_facade"
    ) in gaps
    assert (
        "no_compat_residue:forbidden_identifier:packages/ethos/src/ethos/sample/core.py:"
        "7:compatibility_mode"
    ) in gaps
    assert (
        "no_compat_residue:forbidden_identifier:packages/ethos/src/ethos/sample/core.py:"
        "10:compatibility_wrapper"
    ) in gaps


def test_no_compat_report_handles_paths_outside_configured_source_roots(tmp_path: Path) -> None:
    path = tmp_path / "elsewhere/current.py"
    _write(path, "def current_surface():\n    return 1\n")

    from ethos.repository.policy.no_compat import core

    assert core._module_parts(tmp_path, path) == ()


def test_no_compat_policy_context_allows_layout_vocabulary(tmp_path: Path) -> None:
    _write(
        tmp_path / "packages/ethos/src/ethos/repository/policy/layout/core.py",
        "def compatibility_facade():\n    return None\n",
    )

    report = no_compat_report(tmp_path)

    assert report["ok"] is True
    assert report["required_gaps"] == []
