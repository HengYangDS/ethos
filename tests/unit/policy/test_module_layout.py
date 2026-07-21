from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

import ethos.repository.policy.layout.imports.core as layout_imports
from ethos.repository.policy.layout.core import module_layout_report
from tests.support import write_text as _write


def _write_suffix_baseline_policy(
    root: Path,
    modules: tuple[str, ...],
    baseline_limit: int | None,
) -> None:
    entries = "\n".join(
        f'  "module_layout_suffix_module:packages/ethos/src/ethos/{module}:{Path(module).stem}",'
        for module in modules
    )
    _write(
        root / ".config" / "checks" / "module-layout" / "policy.toml",
        'paths = ["packages/ethos/src"]\n'
        f"{f'baseline_gap_limit = {baseline_limit}\n' if baseline_limit is not None else ''}"
        f"allowed_suffix_modules = [\n{entries}\n]\n",
    )


def _assert_summary_counts(report: dict[str, object], **expected: int) -> None:
    summary = report["summary"]
    assert isinstance(summary, dict)
    for key, value in expected.items():
        assert summary[key] == value


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
    _assert_summary_counts(
        report,
        suffix_module_count=3,
        suffix_flat_count=1,
        flat_directory_count=1,
        private_alias_count=0,
        package_init_facade_count=0,
        module_facade_count=0,
        package_root_submodule_import_count=0,
        flat_growth_count=0,
        baseline_growth_count=0,
        debt_count=5,
    )
    assert report["ratchet"]["state"] == "debt_tracked"
    assert report["ratchet"]["debt_count"] == 5


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
            "\n            from ethos.domain import plan as _plan\n            from ethos.surface.cli._base import emit as _emit\n            "
        ),
    )

    report = module_layout_report(tmp_path)

    assert report["ok"] is False
    assert (
        "module_layout_private_import_alias:packages/ethos/src/ethos/sample.py:ethos.domain.plan->_plan"
    ) in report["required_gaps"]
    assert (
        "module_layout_private_import_alias:packages/ethos/src/ethos/sample.py:ethos.surface.cli._base.emit->_emit"
    ) in report["required_gaps"]


def test_module_layout_flags_package_root_submodule_imports(tmp_path: Path) -> None:
    _write(tmp_path / "packages" / "ethos" / "src" / "ethos" / "sample" / "__init__.py")
    _write(tmp_path / "packages" / "ethos" / "src" / "ethos" / "sample" / "registry.py")
    _write(
        tmp_path / "packages" / "ethos" / "src" / "ethos" / "consumer.py",
        "from ethos.sample import registry as sample_registry\n",
    )

    report = module_layout_report(tmp_path)

    assert report["ok"] is False
    assert (
        "module_layout_package_root_submodule_import:packages/ethos/src/ethos/consumer.py:ethos.sample.registry"
    ) in report["required_gaps"]
    assert report["package_root_submodule_import_findings"] == [
        {
            "gap": (
                "module_layout_package_root_submodule_import:packages/ethos/src/ethos/consumer.py:ethos.sample.registry"
            ),
            "path": "packages/ethos/src/ethos/consumer.py",
            "module": "ethos.sample.registry",
            "imported_from": "ethos.sample",
            "name": "registry",
        }
    ]
    assert report["summary"]["package_root_submodule_import_count"] == 1


def test_module_layout_ignores_non_submodule_package_root_import_forms(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / ".config" / "checks" / "module-layout" / "policy.toml",
        'paths = ["__init__.py", "pkg", "packages/ethos/src"]\n',
    )
    _write(tmp_path / "__init__.py")
    _write(tmp_path / "pkg" / "plain.py")
    _write(tmp_path / "packages" / "ethos" / "src" / "ethos" / "sample" / "__init__.py")
    _write(tmp_path / "packages" / "ethos" / "src" / "ethos" / "sample" / "registry.py")
    _write(
        tmp_path / "packages" / "ethos" / "src" / "ethos" / "consumer.py",
        textwrap.dedent(
            "\n            from .sample import registry\n            from ethos.sample import *\n            from ethos.sample import missing\n            from ethos.sample import registry as _registry\n            "
        ),
    )

    report = module_layout_report(tmp_path)

    assert report["package_root_submodule_import_findings"] == []
    assert report["summary"]["package_root_submodule_import_count"] == 0


def test_module_layout_import_module_name_handles_plain_and_root_init(tmp_path: Path) -> None:
    plain = tmp_path / "plain.py"
    root_init = tmp_path / "__init__.py"
    _write(plain)
    _write(root_init)

    assert layout_imports._module_name(tmp_path, plain) == "plain"
    assert layout_imports._module_name(tmp_path, root_init) == ""


def test_module_layout_flags_package_init_facades(tmp_path: Path) -> None:
    _write(
        tmp_path / "packages" / "ethos" / "src" / "ethos" / "sample" / "__init__.py",
        textwrap.dedent(
            '\n            """Compatibility facade."""\n            from ethos.sample.core import public\n\n            '
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
            "reasons": ["import"],
        }
    ]
    assert report["summary"]["package_init_facade_count"] == 1


def test_module_layout_blocks_stale_baseline_entries(tmp_path: Path) -> None:
    policy = tmp_path / ".config" / "checks" / "module-layout" / "policy.toml"
    _write(
        policy,
        textwrap.dedent(
            '\n            paths = ["packages/ethos/src"]\n            allowed_suffix_modules = [\n              "module_layout_suffix_module:packages/ethos/src/ethos/old_report.py:old_report",\n            ]\n            '
        ),
    )

    report = module_layout_report(tmp_path)

    assert report["ok"] is False
    assert (
        "module_layout_stale_baseline:module_layout_suffix_module:packages/ethos/src/ethos/old_report.py:old_report"
    ) in report["required_gaps"]
    assert report["stale_baseline_findings"] == [
        {
            "gap": (
                "module_layout_stale_baseline:module_layout_suffix_module:packages/ethos/src/ethos/old_report.py:old_report"
            ),
            "baseline_gap": (
                "module_layout_suffix_module:packages/ethos/src/ethos/old_report.py:old_report"
            ),
        }
    ]


@pytest.mark.parametrize(
    ("modules", "baseline_limit", "expected_state", "expected_gap"),
    [
        (
            ("old_report.py", "new_report.py"),
            1,
            "blocked",
            "module_layout_baseline_limit:2>1",
        ),
        (("old_report.py",), None, "blocked", "module_layout_baseline_limit_missing"),
        (("old_report.py",), 2, "blocked", "module_layout_baseline_limit:1!=2"),
        (("old_report.py",), 1, "clean", None),
    ],
    ids=["growth-over-limit", "limit-missing", "limit-count-mismatch", "current-limit"],
)
def test_module_layout_validates_baseline_limit(
    tmp_path: Path,
    modules: tuple[str, ...],
    baseline_limit: int | None,
    expected_state: str,
    expected_gap: str | None,
) -> None:
    source = tmp_path / "packages" / "ethos" / "src" / "ethos"
    for module in modules:
        _write(source / module)
    _write_suffix_baseline_policy(tmp_path, modules, baseline_limit)

    report = module_layout_report(tmp_path)

    assert report["ok"] is (expected_state == "clean")
    assert (expected_gap in report["required_gaps"]) is (expected_gap is not None)


def test_module_layout_clean_state_still_exposes_tracked_ratchet_debt(
    tmp_path: Path,
) -> None:
    source = tmp_path / "packages" / "ethos" / "src" / "ethos"
    _write(source / "old_report.py")
    _write(
        source / "consumer.py",
        "from ethos.domain import plan as _plan\n",
    )
    policy = tmp_path / ".config" / "checks" / "module-layout" / "policy.toml"
    _write(
        policy,
        textwrap.dedent(
            '\n            paths = ["packages/ethos/src"]\n            baseline_gap_limit = 3\n            enforce_baseline_kind_limits = true\n            baseline_suffix_module_limit = 1\n            baseline_suffix_flat_limit = 0\n            baseline_flat_directory_limit = 0\n            baseline_private_alias_limit = 1\n            baseline_package_init_facade_limit = 0\n            baseline_module_facade_limit = 1\n            allowed_suffix_modules = [\n              "module_layout_suffix_module:packages/ethos/src/ethos/old_report.py:old_report",\n            ]\n            allowed_private_aliases = [\n              "module_layout_private_import_alias:packages/ethos/src/ethos/consumer.py:ethos.domain.plan->_plan",\n            ]\n            allowed_module_facades = [\n              "module_layout_module_facade:packages/ethos/src/ethos/consumer.py",\n            ]\n            '
        ),
    )

    report = module_layout_report(tmp_path)

    assert report["ok"] is True
    assert report["state"] == "clean"
    assert report["required_gaps"] == []
    _assert_summary_counts(
        report,
        suffix_module_count=1,
        private_alias_count=1,
        module_facade_count=1,
        debt_count=3,
    )
    assert report["ratchet"] == {
        "state": "debt_tracked",
        "debt_count": 3,
        "debt_kinds": [
            "suffix_module_count",
            "private_alias_count",
            "module_facade_count",
        ],
        "baseline_gap_count": 3,
        "baseline_limit": 3,
        "baseline_kind_counts": {
            "suffix_module": 1,
            "suffix_flat": 0,
            "flat_directory": 0,
            "private_alias": 1,
            "package_init_facade": 0,
            "module_facade": 1,
        },
        "baseline_kind_limits": {
            "suffix_module": 1,
            "suffix_flat": 0,
            "flat_directory": 0,
            "private_alias": 1,
            "package_init_facade": 0,
            "module_facade": 1,
        },
        "next_action": (
            "shrink .config/checks/module-layout/policy.toml baselines when semantic subpackages remove debt; do not add compatibility facades or suffix-flat modules"
        ),
    }


def test_module_layout_accepts_explicit_baseline_kind_limits(tmp_path: Path) -> None:
    source = tmp_path / "packages" / "ethos" / "src" / "ethos"
    _write(source / "old_report.py")
    _write(source / "wide" / "one.py")
    _write(source / "wide" / "two.py")
    _write(source / "wide" / "three.py")
    _write(source / "wide" / "four.py")
    _write(source / "wide" / "five.py")
    _write(source / "wide" / "six.py")
    _write(source / "wide" / "seven.py")
    _write(source / "wide" / "eight.py")
    _write(source / "wide" / "nine.py")
    policy = tmp_path / ".config" / "checks" / "module-layout" / "policy.toml"
    _write(
        policy,
        textwrap.dedent(
            '\n            paths = ["packages/ethos/src"]\n            baseline_gap_limit = 2\n            enforce_baseline_kind_limits = true\n            baseline_suffix_module_limit = 1\n            baseline_suffix_flat_limit = 0\n            baseline_flat_directory_limit = 1\n            baseline_private_alias_limit = 0\n            baseline_package_init_facade_limit = 0\n            baseline_module_facade_limit = 0\n            allowed_suffix_modules = [\n              "module_layout_suffix_module:packages/ethos/src/ethos/old_report.py:old_report",\n            ]\n            allowed_flat_directories = [\n              "module_layout_flat_directory:packages/ethos/src/ethos/wide:9>8",\n            ]\n            '
        ),
    )

    report = module_layout_report(tmp_path)

    assert report["ok"] is True
    assert report["baseline_kind_counts"] == {
        "suffix_module": 1,
        "suffix_flat": 0,
        "flat_directory": 1,
        "private_alias": 0,
        "package_init_facade": 0,
        "module_facade": 0,
    }
    assert report["baseline_kind_limit_findings"] == []


def test_module_layout_blocks_missing_baseline_kind_limit(tmp_path: Path) -> None:
    source = tmp_path / "packages" / "ethos" / "src" / "ethos"
    _write(source / "old_report.py")
    policy = tmp_path / ".config" / "checks" / "module-layout" / "policy.toml"
    _write(
        policy,
        textwrap.dedent(
            '\n            paths = ["packages/ethos/src"]\n            baseline_gap_limit = 1\n            enforce_baseline_kind_limits = true\n            baseline_suffix_module_limit = 1\n            allowed_suffix_modules = [\n              "module_layout_suffix_module:packages/ethos/src/ethos/old_report.py:old_report",\n            ]\n            '
        ),
    )

    report = module_layout_report(tmp_path)

    assert "module_layout_baseline_suffix_flat_limit_missing" in report["required_gaps"]
    assert "module_layout_baseline_flat_directory_limit_missing" in report["required_gaps"]


def test_module_layout_blocks_stale_baseline_kind_limit(tmp_path: Path) -> None:
    source = tmp_path / "packages" / "ethos" / "src" / "ethos"
    _write(source / "old_report.py")
    policy = tmp_path / ".config" / "checks" / "module-layout" / "policy.toml"
    _write(
        policy,
        textwrap.dedent(
            '\n            paths = ["packages/ethos/src"]\n            baseline_gap_limit = 1\n            enforce_baseline_kind_limits = true\n            baseline_suffix_module_limit = 2\n            baseline_suffix_flat_limit = 0\n            baseline_flat_directory_limit = 0\n            baseline_private_alias_limit = 0\n            baseline_package_init_facade_limit = 0\n            baseline_module_facade_limit = 0\n            allowed_suffix_modules = [\n              "module_layout_suffix_module:packages/ethos/src/ethos/old_report.py:old_report",\n            ]\n            '
        ),
    )

    report = module_layout_report(tmp_path)

    assert "module_layout_baseline_suffix_module_limit:1!=2" in report["required_gaps"]
    assert report["baseline_kind_limit_findings"] == [
        {
            "gap": "module_layout_baseline_suffix_module_limit:1!=2",
            "kind": "suffix_module",
            "count": 1,
            "limit": 2,
        }
    ]


def test_module_layout_accepts_single_file_policy_path(tmp_path: Path) -> None:
    target = tmp_path / "packages" / "ethos" / "src" / "ethos" / "one_report.py"
    _write(target)
    policy = tmp_path / ".config" / "checks" / "module-layout" / "policy.toml"
    _write(policy, f'paths = ["{target.relative_to(tmp_path).as_posix()}"]\n')

    report = module_layout_report(tmp_path)

    assert report["required_gaps"] == [
        "module_layout_suffix_module:packages/ethos/src/ethos/one_report.py:one_report"
    ]


def test_module_layout_flags_import_alias_and_runtime_init_code(tmp_path: Path) -> None:
    _write(
        tmp_path / "packages" / "ethos" / "src" / "ethos" / "sample.py",
        textwrap.dedent(
            "\n            import ethos.domain.status\n            import ethos.domain.plan as _plan\n            "
        ),
    )
    _write(
        tmp_path / "packages" / "ethos" / "src" / "ethos" / "runtime" / "__init__.py",
        textwrap.dedent('\n            """Runtime init."""\n            value = 1\n            '),
    )

    report = module_layout_report(tmp_path)

    assert (
        "module_layout_private_import_alias:packages/ethos/src/ethos/sample.py:ethos.domain.plan->_plan"
    ) in report["required_gaps"]
    assert report["package_init_facade_findings"] == [
        {
            "gap": "module_layout_package_init_facade:packages/ethos/src/ethos/runtime/__init__.py",
            "path": "packages/ethos/src/ethos/runtime/__init__.py",
            "reasons": ["runtime_code"],
        }
    ]


def test_module_layout_package_init_facade_with_duplicate_imports(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "packages" / "ethos" / "src" / "ethos" / "facade" / "__init__.py",
        textwrap.dedent(
            '\n            """Facade init."""\n            from ethos.sample.core import one\n            from ethos.sample.core import two\n            '
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
            "reasons": ["import"],
        }
    ]


def test_module_layout_flags_module_import_only_facade(tmp_path: Path) -> None:
    _write(
        tmp_path / "packages" / "ethos" / "src" / "ethos" / "sample" / "core.py",
        textwrap.dedent(
            '\n            """Compatibility import shell."""\n            from __future__ import annotations\n\n            from ethos.sample.report import render\n\n            '
        ),
    )

    report = module_layout_report(tmp_path)

    assert report["ok"] is False
    assert (
        "module_layout_module_facade:packages/ethos/src/ethos/sample/core.py"
        in report["required_gaps"]
    )
    assert report["module_facade_findings"] == [
        {
            "gap": "module_layout_module_facade:packages/ethos/src/ethos/sample/core.py",
            "path": "packages/ethos/src/ethos/sample/core.py",
            "reasons": ["import_only"],
        }
    ]


def test_module_layout_allows_modules_that_define_runtime_symbols(tmp_path: Path) -> None:
    _write(
        tmp_path / "packages" / "ethos" / "src" / "ethos" / "sample" / "core.py",
        textwrap.dedent(
            '\n            """Real module."""\n            from __future__ import annotations\n\n            from ethos.sample.report import render\n\n            def run() -> str:\n                return render()\n            '
        ),
    )

    report = module_layout_report(tmp_path)

    assert report["module_facade_findings"] == []


def test_module_layout_blocks_baseline_growth_from_head(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source = tmp_path / "packages" / "ethos" / "src" / "ethos"
    _write(source / "old_report.py")
    _write(source / "new_report.py")
    policy = tmp_path / ".config" / "checks" / "module-layout" / "policy.toml"
    _write(
        policy,
        textwrap.dedent(
            '\n            paths = ["packages/ethos/src"]\n            baseline_gap_limit = 2\n            allowed_suffix_modules = [\n              "module_layout_suffix_module:packages/ethos/src/ethos/old_report.py:old_report",\n              "module_layout_suffix_module:packages/ethos/src/ethos/new_report.py:new_report",\n            ]\n            '
        ),
    )

    def fake_git(_root: Path, *args: str) -> str | None:
        if args == ("status", "--porcelain"):
            return " M .config/checks/module-layout/policy.toml\n"
        if args == ("rev-parse", "--verify", "HEAD"):
            return "abc\n"
        if args == ("show", "HEAD:.config/checks/module-layout/policy.toml"):
            return textwrap.dedent(
                '\n                paths = ["packages/ethos/src"]\n                baseline_gap_limit = 1\n                allowed_suffix_modules = [\n                  "module_layout_suffix_module:packages/ethos/src/ethos/old_report.py:old_report",\n                ]\n                '
            )
        if args[:5] == ("ls-tree", "-r", "--name-only", "HEAD", "--"):
            return "packages/ethos/src/ethos/old_report.py\n"
        return None

    monkeypatch.setattr("ethos.repository.policy.layout.git.core.run_git", fake_git)

    report = module_layout_report(tmp_path)

    assert (
        "module_layout_baseline_growth:module_layout_suffix_module:packages/ethos/src/ethos/new_report.py:new_report"
    ) in report["required_gaps"]
    assert "module_layout_baseline_limit_growth:2>1" in report["required_gaps"]


def test_module_layout_blocks_flat_growth_in_existing_directory(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source = tmp_path / "packages" / "ethos" / "src" / "ethos" / "sample"
    for name in ("a.py", "b.py", "c.py", "d.py", "e.py", "f.py"):
        _write(source / name)
    _write(tmp_path / ".config" / "checks" / "module-layout" / "policy.toml", "")

    def fake_git(_root: Path, *args: str) -> str | None:
        if args == ("status", "--porcelain"):
            return "?? packages/ethos/src/ethos/sample/f.py\n"
        if args == ("rev-parse", "--verify", "HEAD"):
            return "abc\n"
        if args == ("show", "HEAD:.config/checks/module-layout/policy.toml"):
            return ""
        if args[:5] == ("ls-tree", "-r", "--name-only", "HEAD", "--"):
            return "\n".join(f"packages/ethos/src/ethos/sample/{name}.py" for name in "abcde")
        return None

    monkeypatch.setattr("ethos.repository.policy.layout.git.core.run_git", fake_git)

    report = module_layout_report(tmp_path)

    assert (
        "module_layout_flat_growth:packages/ethos/src/ethos/sample:5+1=6" in report["required_gaps"]
    )


def test_module_layout_blocks_same_directory_add_burst(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source = tmp_path / "packages" / "ethos" / "src" / "ethos" / "sample"
    for name in ("old.py", "one.py", "two.py", "three.py"):
        _write(source / name)
    _write(tmp_path / ".config" / "checks" / "module-layout" / "policy.toml", "")

    def fake_git(_root: Path, *args: str) -> str | None:
        if args == ("status", "--porcelain"):
            return "?? packages/ethos/src/ethos/sample/one.py\n"
        if args == ("rev-parse", "--verify", "HEAD"):
            return "abc\n"
        if args == ("show", "HEAD:.config/checks/module-layout/policy.toml"):
            return ""
        if args[:5] == ("ls-tree", "-r", "--name-only", "HEAD", "--"):
            return "packages/ethos/src/ethos/sample/old.py\n"
        return None

    monkeypatch.setattr("ethos.repository.policy.layout.git.core.run_git", fake_git)

    report = module_layout_report(tmp_path)

    assert (
        "module_layout_flat_growth_burst:packages/ethos/src/ethos/sample:3>2"
        in report["required_gaps"]
    )


def test_module_layout_blocks_new_directory_module_burst(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source = tmp_path / "packages" / "ethos" / "src" / "ethos" / "new_axis"
    for name in ("one.py", "two.py", "three.py"):
        _write(source / name)
    _write(tmp_path / ".config" / "checks" / "module-layout" / "policy.toml", "")

    def fake_git(_root: Path, *args: str) -> str | None:
        if args == ("status", "--porcelain"):
            return "?? packages/ethos/src/ethos/new_axis/one.py\n"
        if args == ("rev-parse", "--verify", "HEAD"):
            return "abc\n"
        if args == ("show", "HEAD:.config/checks/module-layout/policy.toml"):
            return ""
        if args[:5] == ("ls-tree", "-r", "--name-only", "HEAD", "--"):
            return ""
        return None

    monkeypatch.setattr("ethos.repository.policy.layout.git.core.run_git", fake_git)

    report = module_layout_report(tmp_path)

    assert (
        "module_layout_new_directory_burst:packages/ethos/src/ethos/new_axis:3>2"
        in report["required_gaps"]
    )


def test_module_layout_blocks_dynamic_compatibility_export_module(tmp_path: Path) -> None:
    _write(
        tmp_path / "packages" / "ethos" / "src" / "ethos" / "sample" / "compat.py",
        textwrap.dedent(
            '\n            """Dynamic compatibility export shell."""\n            from __future__ import annotations\n\n            def __getattr__(name: str) -> object:\n                from ethos.sample.core import value\n                if name == "value":\n                    return value\n                raise AttributeError(name)\n            '
        ),
    )

    report = module_layout_report(tmp_path)

    assert (
        "module_layout_dynamic_compat_facade:packages/ethos/src/ethos/sample/compat.py"
        in report["required_gaps"]
    )
    assert report["dynamic_compat_facade_findings"] == [
        {
            "gap": (
                "module_layout_dynamic_compat_facade:packages/ethos/src/ethos/sample/compat.py"
            ),
            "path": "packages/ethos/src/ethos/sample/compat.py",
            "reasons": ["dynamic_export", "lazy_import"],
        }
    ]


def test_module_layout_blocks_dynamic_export_without_lazy_import(tmp_path: Path) -> None:
    _write(
        tmp_path / "packages" / "ethos" / "src" / "ethos" / "sample" / "virtual.py",
        textwrap.dedent(
            '\n            """Dynamic local virtual attribute shell."""\n\n            def __getattr__(name: str) -> object:\n                if name == "value":\n                    return 1\n                raise AttributeError(name)\n            '
        ),
    )

    report = module_layout_report(tmp_path)

    assert report["dynamic_compat_facade_findings"] == [
        {
            "gap": (
                "module_layout_dynamic_compat_facade:packages/ethos/src/ethos/sample/virtual.py"
            ),
            "path": "packages/ethos/src/ethos/sample/virtual.py",
            "reasons": ["dynamic_export"],
        }
    ]


def test_lane_lifecycle_modules_do_not_import_sibling_private_helpers() -> None:
    targets = (
        "packages/ethos/src/ethos/adapters/mutation/lanes.py",
        "packages/ethos/src/ethos/adapters/mutation/lane_lifecycle/refresh.py",
    )
    forbidden = "from ethos.adapters.mutation.lanes_retire import _"

    offenders = [path for path in targets if forbidden in Path(path).read_text(encoding="utf-8")]

    assert offenders == []


def test_lane_retirement_has_one_linked_owner_and_independent_unbound_boundary() -> None:
    old_module = Path("packages/ethos/src/ethos/adapters/mutation/lanes_retire.py")
    linked_owner = Path("packages/ethos/src/ethos/adapters/mutation/lane_retirement/core.py")
    landed_package = Path("packages/ethos/src/ethos/adapters/mutation/lane_retirement/landed")
    lanes_source = Path("packages/ethos/src/ethos/adapters/mutation/lanes.py").read_text(
        encoding="utf-8"
    )
    cli_source = Path("packages/ethos/src/ethos/surface/cli/lane/core.py").read_text(
        encoding="utf-8"
    )

    assert not old_module.exists()
    assert "lanes_retire" not in lanes_source
    assert linked_owner.exists()
    assert not landed_package.exists()
    assert "lane_retirement.landed" not in cli_source
    assert Path(
        "packages/ethos/src/ethos/adapters/mutation/lane_retirement/unbound/core.py"
    ).exists()
