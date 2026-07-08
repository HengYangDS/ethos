from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.policy.layout.core import module_layout_report

if TYPE_CHECKING:
    from pathlib import Path


def _write(path: Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_module_layout_blocks_private_from_import_regression(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write(
        tmp_path / "packages" / "ethos" / "src" / "ethos" / "consumer.py",
        "from ethos.sample.provider import _private_helper\n",
    )
    _write(tmp_path / ".config" / "checks" / "module-layout" / "policy.toml", "")

    def fake_git(_root: Path, *args: str) -> str | None:
        if args == ("status", "--porcelain"):
            return " M packages/ethos/src/ethos/consumer.py\n"
        if args == ("rev-parse", "--verify", "HEAD"):
            return "abc\n"
        if args == ("show", "HEAD:.config/checks/module-layout/policy.toml"):
            return ""
        if args[:3] == ("diff", "--name-only", "HEAD"):
            return "packages/ethos/src/ethos/consumer.py\n"
        if args[:5] == ("ls-tree", "-r", "--name-only", "HEAD", "--"):
            return "packages/ethos/src/ethos/consumer.py\n"
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
        if args == ("status", "--porcelain"):
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
