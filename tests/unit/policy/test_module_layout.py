from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from ethos.repository.policy.layout.core import module_layout_report


def _write(path: Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_module_layout_flags_suffix_flat_groups_and_flat_directory(tmp_path: Path) -> None:
    source = tmp_path / "packages" / "ethos" / "src" / "ethos" / "sample"
    for name in (
        "__init__.py",
        "thing_report.py",
        "thing_native.py",
        "thing_index.py",
        "a.py",
        "b.py",
        "c.py",
        "d.py",
        "e.py",
        "f.py",
    ):
        _write(source / name)

    report = module_layout_report(tmp_path)

    assert report["ok"] is False
    assert (
        "module_layout_suffix_flat:packages/ethos/src/ethos/sample:thing:3"
        in report["required_gaps"]
    )
    assert (
        "module_layout_flat_directory:packages/ethos/src/ethos/sample:9>8"
        in report["required_gaps"]
    )
    assert report["summary"] == {
        "suffix_module_count": 3,
        "suffix_flat_count": 1,
        "flat_directory_count": 1,
        "private_alias_count": 0,
        "package_init_facade_count": 0,
    }


def test_module_layout_flags_single_suffix_flat_module(tmp_path: Path) -> None:
    _write(tmp_path / "packages" / "ethos" / "src" / "ethos" / "sample" / "thing_report.py")

    report = module_layout_report(tmp_path)

    assert report["ok"] is False
    assert (
        "module_layout_suffix_module:packages/ethos/src/ethos/sample/thing_report.py:thing_report"
    ) in report["required_gaps"]


def test_module_layout_flags_private_alias_compat_imports(tmp_path: Path) -> None:
    _write(
        tmp_path / "packages" / "ethos" / "src" / "ethos" / "sample.py",
        textwrap.dedent(
            """
            from ethos.domain import plan as _plan
            from ethos.surface.cli._base import emit as _emit
            """
        ),
    )

    report = module_layout_report(tmp_path)

    assert report["ok"] is False
    assert (
        "module_layout_private_import_alias:"
        "packages/ethos/src/ethos/sample.py:ethos.domain.plan->_plan"
    ) in report["required_gaps"]
    assert (
        "module_layout_private_import_alias:"
        "packages/ethos/src/ethos/sample.py:ethos.surface.cli._base.emit->_emit"
    ) in report["required_gaps"]


def test_module_layout_flags_package_init_facades(tmp_path: Path) -> None:
    _write(
        tmp_path / "packages" / "ethos" / "src" / "ethos" / "sample" / "__init__.py",
        textwrap.dedent(
            '''
            """Compatibility facade."""
            from ethos.sample.core import public

            __all__ = ["public"]
            '''
        ),
    )

    report = module_layout_report(tmp_path)

    assert report["ok"] is False
    assert (
        "module_layout_package_init_facade:packages/ethos/src/ethos/sample/__init__.py"
    ) in report["required_gaps"]
    assert report["package_init_facade_findings"] == [
        {
            "gap": "module_layout_package_init_facade:packages/ethos/src/ethos/sample/__init__.py",
            "path": "packages/ethos/src/ethos/sample/__init__.py",
            "reasons": ["import", "explicit_exports"],
        }
    ]
    assert report["summary"]["package_init_facade_count"] == 1


def test_module_layout_blocks_stale_baseline_entries(tmp_path: Path) -> None:
    policy = tmp_path / ".config" / "checks" / "module-layout" / "policy.toml"
    _write(
        policy,
        textwrap.dedent(
            """
            paths = ["packages/ethos/src"]
            allowed_suffix_modules = [
              "module_layout_suffix_module:packages/ethos/src/ethos/old_report.py:old_report",
            ]
            """
        ),
    )

    report = module_layout_report(tmp_path)

    assert report["ok"] is False
    assert (
        "module_layout_stale_baseline:"
        "module_layout_suffix_module:packages/ethos/src/ethos/old_report.py:old_report"
    ) in report["required_gaps"]
    assert report["stale_baseline_findings"] == [
        {
            "gap": (
                "module_layout_stale_baseline:"
                "module_layout_suffix_module:packages/ethos/src/ethos/old_report.py:old_report"
            ),
            "baseline_gap": (
                "module_layout_suffix_module:packages/ethos/src/ethos/old_report.py:old_report"
            ),
        }
    ]


def test_module_layout_blocks_baseline_growth_over_ratchet_limit(tmp_path: Path) -> None:
    source = tmp_path / "packages" / "ethos" / "src" / "ethos"
    _write(source / "old_report.py")
    _write(source / "new_report.py")
    policy = tmp_path / ".config" / "checks" / "module-layout" / "policy.toml"
    _write(
        policy,
        textwrap.dedent(
            """
            paths = ["packages/ethos/src"]
            baseline_gap_limit = 1
            allowed_suffix_modules = [
              "module_layout_suffix_module:packages/ethos/src/ethos/old_report.py:old_report",
              "module_layout_suffix_module:packages/ethos/src/ethos/new_report.py:new_report",
            ]
            """
        ),
    )

    report = module_layout_report(tmp_path)

    assert report["ok"] is False
    assert "module_layout_baseline_limit:2>1" in report["required_gaps"]
    assert report["baseline_limit"] == 1


def test_module_layout_requires_baseline_limit_when_baseline_exists(tmp_path: Path) -> None:
    source = tmp_path / "packages" / "ethos" / "src" / "ethos"
    _write(source / "old_report.py")
    policy = tmp_path / ".config" / "checks" / "module-layout" / "policy.toml"
    _write(
        policy,
        textwrap.dedent(
            """
            paths = ["packages/ethos/src"]
            allowed_suffix_modules = [
              "module_layout_suffix_module:packages/ethos/src/ethos/old_report.py:old_report",
            ]
            """
        ),
    )

    report = module_layout_report(tmp_path)

    assert report["ok"] is False
    assert "module_layout_baseline_limit_missing" in report["required_gaps"]


def test_module_layout_requires_baseline_limit_to_match_current_baseline_count(
    tmp_path: Path,
) -> None:
    source = tmp_path / "packages" / "ethos" / "src" / "ethos"
    _write(source / "old_report.py")
    policy = tmp_path / ".config" / "checks" / "module-layout" / "policy.toml"
    _write(
        policy,
        textwrap.dedent(
            """
            paths = ["packages/ethos/src"]
            baseline_gap_limit = 2
            allowed_suffix_modules = [
              "module_layout_suffix_module:packages/ethos/src/ethos/old_report.py:old_report",
            ]
            """
        ),
    )

    report = module_layout_report(tmp_path)

    assert report["ok"] is False
    assert "module_layout_baseline_limit:1!=2" in report["required_gaps"]


def test_module_layout_accepts_current_baseline_limit(tmp_path: Path) -> None:
    source = tmp_path / "packages" / "ethos" / "src" / "ethos"
    _write(source / "old_report.py")
    policy = tmp_path / ".config" / "checks" / "module-layout" / "policy.toml"
    _write(
        policy,
        textwrap.dedent(
            """
            paths = ["packages/ethos/src"]
            baseline_gap_limit = 1
            allowed_suffix_modules = [
              "module_layout_suffix_module:packages/ethos/src/ethos/old_report.py:old_report",
            ]
            """
        ),
    )

    report = module_layout_report(tmp_path)

    assert report["ok"] is True
    assert report["required_gaps"] == []


def test_module_layout_accepts_single_file_policy_path(tmp_path: Path) -> None:
    target = tmp_path / "packages" / "ethos" / "src" / "ethos" / "one_report.py"
    _write(target)
    policy = tmp_path / ".config" / "checks" / "module-layout" / "policy.toml"
    _write(
        policy,
        textwrap.dedent(
            f"""
            paths = ["{target.relative_to(tmp_path).as_posix()}"]
            """
        ),
    )

    report = module_layout_report(tmp_path)

    assert report["required_gaps"] == [
        "module_layout_suffix_module:packages/ethos/src/ethos/one_report.py:one_report"
    ]


def test_module_layout_flags_import_alias_and_runtime_init_code(tmp_path: Path) -> None:
    _write(
        tmp_path / "packages" / "ethos" / "src" / "ethos" / "sample.py",
        textwrap.dedent(
            """
            import ethos.domain.status
            import ethos.domain.plan as _plan
            """
        ),
    )
    _write(
        tmp_path / "packages" / "ethos" / "src" / "ethos" / "runtime" / "__init__.py",
        textwrap.dedent(
            '''
            """Runtime init."""
            value = 1
            '''
        ),
    )

    report = module_layout_report(tmp_path)

    assert (
        "module_layout_private_import_alias:"
        "packages/ethos/src/ethos/sample.py:ethos.domain.plan->_plan"
    ) in report["required_gaps"]
    assert report["package_init_facade_findings"] == [
        {
            "gap": "module_layout_package_init_facade:packages/ethos/src/ethos/runtime/__init__.py",
            "path": "packages/ethos/src/ethos/runtime/__init__.py",
            "reasons": ["runtime_code"],
        }
    ]


def test_module_layout_package_init_all_annotation_and_duplicate_reasons(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "packages" / "ethos" / "src" / "ethos" / "facade" / "__init__.py",
        textwrap.dedent(
            '''
            """Facade init."""
            from ethos.sample.core import one
            from ethos.sample.core import two
            __all__: list[str] = ["one", "two"]
            '''
        ),
    )
    _write(
        tmp_path / "packages" / "ethos" / "src" / "ethos" / "clean" / "__init__.py",
        '"""Declaration-only init."""\npass\n',
    )

    report = module_layout_report(tmp_path)

    assert report["package_init_facade_findings"] == [
        {
            "gap": "module_layout_package_init_facade:packages/ethos/src/ethos/facade/__init__.py",
            "path": "packages/ethos/src/ethos/facade/__init__.py",
            "reasons": ["import", "explicit_exports"],
        }
    ]
