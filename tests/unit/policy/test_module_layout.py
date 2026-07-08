from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import ethos.repository.policy.layout.imports.core as layout_imports
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
        "module_facade_count": 0,
        "package_root_submodule_import_count": 0,
        "flat_growth_count": 0,
        "baseline_growth_count": 0,
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
        "module_layout_package_root_submodule_import:"
        "packages/ethos/src/ethos/consumer.py:ethos.sample.registry"
    ) in report["required_gaps"]
    assert report["package_root_submodule_import_findings"] == [
        {
            "gap": (
                "module_layout_package_root_submodule_import:"
                "packages/ethos/src/ethos/consumer.py:ethos.sample.registry"
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
            """
            from .sample import registry
            from ethos.sample import *
            from ethos.sample import missing
            from ethos.sample import registry as _registry
            """
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


def test_module_layout_flags_module_import_only_facade(tmp_path: Path) -> None:
    _write(
        tmp_path / "packages" / "ethos" / "src" / "ethos" / "sample" / "core.py",
        textwrap.dedent(
            '''
            """Compatibility import shell."""
            from __future__ import annotations

            from ethos.sample.report import render

            __all__ = ["render"]
            '''
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
            "reasons": ["import_only", "explicit_exports"],
        }
    ]


def test_module_layout_allows_modules_that_define_runtime_symbols(tmp_path: Path) -> None:
    _write(
        tmp_path / "packages" / "ethos" / "src" / "ethos" / "sample" / "core.py",
        textwrap.dedent(
            '''
            """Real module."""
            from __future__ import annotations

            from ethos.sample.report import render

            def run() -> str:
                return render()
            '''
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
            """
            paths = ["packages/ethos/src"]
            baseline_gap_limit = 2
            allowed_suffix_modules = [
              "module_layout_suffix_module:packages/ethos/src/ethos/old_report.py:old_report",
              "module_layout_suffix_module:packages/ethos/src/ethos/new_report.py:new_report",
            ]
            """
        ),
    )

    def fake_git(_root: Path, *args: str) -> str | None:
        if args == ("status", "--porcelain"):
            return " M .config/checks/module-layout/policy.toml\n"
        if args == ("rev-parse", "--verify", "HEAD"):
            return "abc\n"
        if args == ("show", "HEAD:.config/checks/module-layout/policy.toml"):
            return textwrap.dedent(
                """
                paths = ["packages/ethos/src"]
                baseline_gap_limit = 1
                allowed_suffix_modules = [
                  "module_layout_suffix_module:packages/ethos/src/ethos/old_report.py:old_report",
                ]
                """
            )
        if args[:5] == ("ls-tree", "-r", "--name-only", "HEAD", "--"):
            return "packages/ethos/src/ethos/old_report.py\n"
        return None

    monkeypatch.setattr("ethos.repository.policy.layout.git.core.run_git", fake_git)

    report = module_layout_report(tmp_path)

    assert (
        "module_layout_baseline_growth:"
        "module_layout_suffix_module:packages/ethos/src/ethos/new_report.py:new_report"
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


def test_module_layout_baseline_growth_skips_without_reference(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from ethos.repository.policy.layout.baseline.core import baseline_growth_findings
    from ethos.repository.policy.layout.baseline.core import previous_policy_at_reference

    monkeypatch.setattr(
        "ethos.repository.policy.layout.git.core.layout_reference", lambda _root: None
    )

    policy = {"baseline_gap_limit": 1}
    assert previous_policy_at_reference(tmp_path, policy) is None
    assert baseline_growth_findings(tmp_path, policy, {"gap"}) == []


def test_module_layout_baseline_growth_uses_current_policy_when_reference_policy_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from ethos.repository.policy.layout.baseline.core import baseline_growth_findings
    from ethos.repository.policy.layout.baseline.core import previous_policy_at_reference

    monkeypatch.setattr(
        "ethos.repository.policy.layout.git.core.layout_reference", lambda _root: "HEAD"
    )
    monkeypatch.setattr("ethos.repository.policy.layout.git.core.run_git_show", lambda *_args: None)

    policy = {"baseline_gap_limit": 1, "allowed_suffix_modules": ["gap"]}
    assert previous_policy_at_reference(tmp_path, policy) is policy
    assert baseline_growth_findings(tmp_path, policy, {"gap"}) == []


def test_module_layout_facade_type_checking_and_private_alias_edges(tmp_path: Path) -> None:
    _write(
        tmp_path / "packages" / "ethos" / "src" / "ethos" / "sample" / "facade.py",
        textwrap.dedent(
            '''
            """Type-checking import shell."""
            from typing import TYPE_CHECKING

            if TYPE_CHECKING:
                from ethos.sample.core import Item
            '''
        ),
    )
    _write(
        tmp_path / "packages" / "ethos" / "src" / "ethos" / "sample" / "plain.py",
        "import ethos.domain.plan\n",
    )
    _write(
        tmp_path / "packages" / "ethos" / "src" / "ethos" / "sample" / "alias.py",
        "import ethos.domain.plan as plan\nfrom ethos.domain.plan import graph_for_paths\n",
    )
    _write(
        tmp_path / "packages" / "ethos" / "src" / "ethos" / "sample" / "annotated.py",
        textwrap.dedent(
            '''
            """Annotated exports."""
            from ethos.sample.core import item
            __all__: list[str] = ["item"]
            '''
        ),
    )
    _write(
        tmp_path / "packages" / "ethos" / "src" / "ethos" / "sample" / "pass_shell.py",
        textwrap.dedent(
            '''
            """Import shell with pass residue."""
            from ethos.sample.core import item

            pass
            '''
        ),
    )
    _write(
        tmp_path / "packages" / "ethos" / "src" / "ethos" / "sample" / "debug_guard.py",
        textwrap.dedent(
            '''
            """Import shell with a non-type-checking branch."""
            from ethos.sample.core import item

            if DEBUG:
                pass
            '''
        ),
    )

    report = module_layout_report(tmp_path)

    assert (
        "module_layout_module_facade:packages/ethos/src/ethos/sample/facade.py"
        in report["required_gaps"]
    )
    assert (
        "module_layout_module_facade:packages/ethos/src/ethos/sample/plain.py"
        in report["required_gaps"]
    )
    assert report["module_facade_findings"][-1] == {
        "gap": "module_layout_module_facade:packages/ethos/src/ethos/sample/plain.py",
        "path": "packages/ethos/src/ethos/sample/plain.py",
        "reasons": ["import_only"],
    }
    assert report["private_alias_findings"] == []
    assert any(
        item["path"] == "packages/ethos/src/ethos/sample/annotated.py"
        and item["reasons"] == ["import_only", "explicit_exports"]
        for item in report["module_facade_findings"]
    )
    assert any(
        item["path"] == "packages/ethos/src/ethos/sample/pass_shell.py"
        and item["reasons"] == ["import_only"]
        for item in report["module_facade_findings"]
    )
    assert all(
        item["path"] != "packages/ethos/src/ethos/sample/debug_guard.py"
        for item in report["module_facade_findings"]
    )


def test_module_layout_growth_edges_and_git_helpers(tmp_path: Path, monkeypatch) -> None:
    from ethos.repository.policy.layout.git.core import layout_reference
    from ethos.repository.policy.layout.git.core import run_git
    from ethos.repository.policy.layout.git.core import run_git as direct_run_git
    from ethos.repository.policy.layout.growth.core import flat_growth_findings
    from ethos.repository.policy.layout.growth.core import module_counts_by_directory
    from ethos.repository.policy.layout.growth.core import reference_python_files

    assert run_git(tmp_path, "rev-parse", "--is-inside-work-tree") is None

    class Completed:
        returncode = 0
        stdout = "ok\n"

    def fake_subprocess_run(*_args: object, **_kwargs: object) -> Completed:
        return Completed()

    monkeypatch.setattr(
        "ethos.repository.policy.layout.git.core.subprocess.run",
        fake_subprocess_run,
    )
    assert direct_run_git(tmp_path, "status", "--porcelain") == "ok\n"

    calls: list[tuple[str, ...]] = []
    fake_outputs = {
        ("status", "--porcelain"): "",
        ("rev-parse", "--verify", "candidate/dev"): None,
        ("rev-parse", "--verify", "dev"): "dev\n",
        ("show", "dev:packages/ethos/src/ethos/one.py"): "print('old')\n",
        ("show", "dev:packages/ethos/src"): None,
        ("show", "dev:packages/ethos/missing"): None,
        ("ls-tree", "-r", "--name-only", "dev", "--", "packages/ethos/src"): (
            "packages/ethos/src/ethos/sample/old.py\n"
            "packages/ethos/src/ethos/sample/__init__.py\n"
            "packages/ethos/src/ethos/sample/__pycache__/skip.py"
        ),
        ("ls-tree", "-r", "--name-only", "dev", "--", "packages/ethos/missing"): None,
    }

    def fake_git(_root: Path, *args: str) -> str | None:
        calls.append(args)
        return fake_outputs.get(args)

    monkeypatch.setattr("ethos.repository.policy.layout.git.core.run_git", fake_git)

    assert layout_reference(tmp_path) == "dev"
    assert reference_python_files(
        tmp_path, {"paths": ["packages/ethos/src/ethos/one.py"]}, "dev"
    ) == {"packages/ethos/src/ethos/one.py"}
    assert reference_python_files(
        tmp_path,
        {"paths": ["packages/ethos/src", "packages/ethos/missing"]},
        "dev",
    ) == {
        "packages/ethos/src/ethos/sample/old.py",
        "packages/ethos/src/ethos/sample/__init__.py",
    }

    _write(tmp_path / "packages" / "ethos" / "src" / "ethos" / "sample" / "old.py")
    assert flat_growth_findings(tmp_path, {"paths": ["packages/ethos/src"]}) == []
    _write(tmp_path / "packages" / "ethos" / "src" / "ethos" / "newdir" / "one.py")
    _write(tmp_path / "packages" / "ethos" / "src" / "ethos" / "sample" / "new.py")
    assert flat_growth_findings(tmp_path, {"paths": ["packages/ethos/src"]}) == []
    assert module_counts_by_directory(
        {
            "packages/ethos/src/ethos/sample/__init__.py",
            "packages/ethos/src/ethos/sample/old.py",
        }
    ) == {"packages/ethos/src/ethos/sample": 1}
    assert ("rev-parse", "--verify", "candidate/dev") in calls
