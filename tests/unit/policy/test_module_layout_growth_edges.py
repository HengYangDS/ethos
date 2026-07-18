from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING

from ethos.repository.policy.layout.core import module_layout_report
from tests.unit.policy.test_module_layout import _write

if TYPE_CHECKING:
    from pathlib import Path


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
