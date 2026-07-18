from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.policy.layout.core import module_layout_report
from ethos.repository.policy.layout.imports.core import _status_paths
from ethos.repository.policy.layout.imports.core import private_from_import_regression_findings
from tests.support import write_text as _write

if TYPE_CHECKING:
    from pathlib import Path


def test_module_layout_blocks_private_from_import_regression(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write(
        tmp_path / "packages" / "ethos" / "src" / "ethos" / "consumer.py",
        "from ethos.sample.provider import _private_helper\n",
    )
    _write(
        tmp_path / "packages" / "ethos" / "src" / "ethos" / "unchanged.py",
        "from ethos.sample.provider import _legacy_private_helper\n",
    )
    _write(tmp_path / ".config" / "checks" / "module-layout" / "policy.toml", "")

    def fake_git(_root: Path, *args: str) -> str | None:
        if args[:2] == ("status", "--porcelain"):
            return " M packages/ethos/src/ethos/consumer.py\n"
        if args == ("rev-parse", "--verify", "HEAD"):
            return "abc\n"
        if args == ("show", "HEAD:.config/checks/module-layout/policy.toml"):
            return ""
        if args[:3] == ("diff", "--name-only", "HEAD"):
            return "packages/ethos/src/ethos/consumer.py\n"
        if args[:5] == ("ls-tree", "-r", "--name-only", "HEAD", "--"):
            return "packages/ethos/src/ethos/consumer.py\npackages/ethos/src/ethos/unchanged.py\n"
        return None

    monkeypatch.setattr("ethos.repository.policy.layout.git.core.run_git", fake_git)

    report = module_layout_report(tmp_path)

    gap = (
        "module_layout_private_from_import:"
        "packages/ethos/src/ethos/consumer.py:"
        "ethos.sample.provider->_private_helper"
    )
    assert report["private_from_import_regression_findings"] == [
        {
            "gap": gap,
            "path": "packages/ethos/src/ethos/consumer.py",
            "module": "ethos.sample.provider",
            "name": "_private_helper",
        }
    ]
    assert gap in report["required_gaps"]


def test_module_layout_does_not_block_unchanged_private_from_import_debt(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write(
        tmp_path / "packages" / "ethos" / "src" / "ethos" / "legacy.py",
        "from ethos.sample.provider import _private_helper\n",
    )
    _write(tmp_path / ".config" / "checks" / "module-layout" / "policy.toml", "")

    def fake_git(_root: Path, *args: str) -> str | None:
        if args[:2] == ("status", "--porcelain"):
            return ""
        if args == ("rev-parse", "--verify", "candidate/dev"):
            return "abc\n"
        if args == ("show", "candidate/dev:.config/checks/module-layout/policy.toml"):
            return ""
        if args[:3] == ("diff", "--name-only", "candidate/dev"):
            return ""
        if args[:5] == ("ls-tree", "-r", "--name-only", "candidate/dev", "--"):
            return "packages/ethos/src/ethos/legacy.py\n"
        return None

    monkeypatch.setattr("ethos.repository.policy.layout.git.core.run_git", fake_git)

    report = module_layout_report(tmp_path)

    assert report["private_from_import_regression_findings"] == []
    assert not any(
        str(gap).startswith("module_layout_private_from_import:") for gap in report["required_gaps"]
    )


def test_import_discipline_ignores_relative_star_dunder_and_rename_status(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write(
        tmp_path / "packages" / "ethos" / "src" / "ethos" / "renamed.py",
        "from .provider import _relative_private\n"
        "from ethos.sample.provider import *\n"
        "from ethos.sample.provider import __dunder_private\n",
    )
    _write(tmp_path / ".config" / "checks" / "module-layout" / "policy.toml", "")

    def fake_git(_root: Path, *args: str) -> str | None:
        if args[:2] == ("status", "--porcelain"):
            return "\nR  packages/ethos/src/ethos/old.py -> packages/ethos/src/ethos/renamed.py\n"
        if args == ("rev-parse", "--verify", "HEAD"):
            return "abc\n"
        if args == ("show", "HEAD:.config/checks/module-layout/policy.toml"):
            return ""
        if args[:3] == ("diff", "--name-only", "HEAD"):
            return "packages/ethos/src/ethos/renamed.py\n"
        if args[:5] == ("ls-tree", "-r", "--name-only", "HEAD", "--"):
            return "packages/ethos/src/ethos/renamed.py\n"
        return None

    monkeypatch.setattr("ethos.repository.policy.layout.git.core.run_git", fake_git)

    report = module_layout_report(tmp_path)

    assert report["private_from_import_regression_findings"] == []
    assert not any(
        str(gap).startswith("module_layout_private_from_import:") for gap in report["required_gaps"]
    )


def test_import_discipline_status_parser_covers_blank_short_and_normal_paths(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write(
        tmp_path / "packages" / "ethos" / "src" / "ethos" / "normal.py",
        "from ethos.sample.provider import _private_helper\n",
    )
    _write(tmp_path / ".config" / "checks" / "module-layout" / "policy.toml", "")

    def fake_git(_root: Path, *args: str) -> str | None:
        if args[:2] == ("status", "--porcelain"):
            return "\n??\n M packages/ethos/src/ethos/normal.py\n"
        if args == ("rev-parse", "--verify", "HEAD"):
            return "abc\n"
        if args == ("show", "HEAD:.config/checks/module-layout/policy.toml"):
            return ""
        if args[:3] == ("diff", "--name-only", "HEAD"):
            return ""
        if args[:5] == ("ls-tree", "-r", "--name-only", "HEAD", "--"):
            return "packages/ethos/src/ethos/normal.py\n"
        return None

    monkeypatch.setattr("ethos.repository.policy.layout.git.core.run_git", fake_git)

    report = module_layout_report(tmp_path)

    assert report["private_from_import_regression_findings"] == [
        {
            "gap": (
                "module_layout_private_from_import:"
                "packages/ethos/src/ethos/normal.py:"
                "ethos.sample.provider->_private_helper"
            ),
            "path": "packages/ethos/src/ethos/normal.py",
            "module": "ethos.sample.provider",
            "name": "_private_helper",
        }
    ]


def test_import_discipline_skips_python_files_not_changed_from_reference(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write(
        tmp_path / "packages" / "ethos" / "src" / "ethos" / "changed.py",
        "VALUE = 1\n",
    )
    _write(
        tmp_path / "packages" / "ethos" / "src" / "ethos" / "unchanged.py",
        "from ethos.sample.provider import _private_helper\n",
    )

    def fake_git(_root: Path, *args: str) -> str | None:
        if args[:3] == ("diff", "--name-only", "HEAD"):
            return "packages/ethos/src/ethos/changed.py\n"
        if args[:2] == ("status", "--porcelain"):
            return ""
        return None

    monkeypatch.setattr(
        "ethos.repository.policy.layout.git.core.layout_reference", lambda _root: "HEAD"
    )
    monkeypatch.setattr("ethos.repository.policy.layout.git.core.run_git", fake_git)

    assert private_from_import_regression_findings(tmp_path, {}) == []


def test_import_discipline_ignores_package_root_star_and_private_alias(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "packages" / "ethos" / "src" / "ethos" / "provider.py",
        "VALUE = 1\n",
    )
    _write(
        tmp_path / "packages" / "ethos" / "src" / "ethos" / "consumer.py",
        "from ethos import *\nfrom ethos import provider as _provider\n",
    )
    _write(tmp_path / ".config" / "checks" / "module-layout" / "policy.toml", "")

    report = module_layout_report(tmp_path)

    assert report["package_root_submodule_import_findings"] == []
    assert not any(
        str(gap).startswith("module_layout_package_root_submodule_import:")
        for gap in report["required_gaps"]
    )


def test_status_path_parser_handles_blank_short_normal_and_renamed_entries() -> None:
    assert _status_paths(
        "\n"
        "??\n"
        " M packages/ethos/src/ethos/changed.py\n"
        "R  packages/ethos/src/ethos/old.py -> packages/ethos/src/ethos/new.py\n"
    ) == {
        "packages/ethos/src/ethos/changed.py",
        "packages/ethos/src/ethos/new.py",
    }
