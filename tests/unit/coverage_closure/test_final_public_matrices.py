"""Compact public failure matrices for the final coverage closure."""

from __future__ import annotations

import ast
import subprocess
from types import SimpleNamespace
from typing import TYPE_CHECKING

import ethos.adapters.gates.runner as gate_runner
import ethos.adapters.repo.status.workspace as workspace
import ethos.repository.policy.layout.imports as layout_imports
from ethos.contracts.gates import Gate
from ethos.contracts.plan import PlanNode
from ethos.repository.policy.references.python_syntax import cyclopts_command_owners
from ethos.repository.policy.references.python_syntax import cyclopts_prefixes
from ethos.repository.policy.references.python_syntax import module_name

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_layout_import_public_matrices(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    package = tmp_path / "src/pkg"
    package.mkdir(parents=True)
    files = {
        tmp_path / "__init__.py": "",
        tmp_path / "tools.py": "VALUE = 1\n",
        package / "__init__.py": "",
        package / "child.py": "VALUE = 1\n",
        package / "consumer.py": (
            "from pkg import *\n"
            "from pkg import child as _hidden\n"
            "from pkg import child, missing\n"
            "from pkg.child import *\n"
            "from pkg.child import __dunder, _private, public\n"
        ),
    }
    for path, text in files.items():
        path.write_text(text, encoding="utf-8")
    paths = tuple(files)
    monkeypatch.setattr(layout_imports, "package_python_files", lambda *_a, **_k: paths)
    monkeypatch.setattr(layout_imports, "semantic_python_files", lambda *_a, **_k: paths)

    roots = layout_imports.package_root_submodule_import_findings(tmp_path, {}, paths)
    private = layout_imports.private_from_import_findings(tmp_path, {}, paths)

    assert [item["module"] for item in roots] == ["pkg.child"]
    assert [item["name"] for item in private] == ["_private"]


def test_python_syntax_public_edge_matrix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "ethos.repository.policy.references.python_syntax.python_trees", lambda _text: ()
    )
    assert cyclopts_prefixes({"src/pkg/cli.py": "App("}) == {}
    monkeypatch.undo()

    files = {
        "src/pkg/cli.py": (
            "a_app = App(name='alpha')\n"
            "b_app = App(name='beta')\n"
            "a_app.command(b_app)\n"
            "b_app.command(a_app)\n"
        )
    }
    prefixes = cyclopts_prefixes(files)
    assert prefixes[("pkg.cli", "a_app")] == "beta alpha"
    assert prefixes[("pkg.cli", "b_app")] == "alpha beta"
    assert module_name("src/pkg/__init__.py") == "pkg"

    tree = ast.parse("@app.command(name='explicit')\ndef default_name(): pass\n")
    assert set(
        cyclopts_command_owners("src/pkg/command.py", tree, {("pkg.command", "app"): "root"})
    ) == {"root explicit"}


def test_gate_result_and_provider_public_edges(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    assert gate_runner.classify_action_result(exit_code=1, stdout="{}")[0] == "block"
    assert gate_runner.classify_action_result(exit_code=0, stdout='{"value": 1}') == ("pass", ())
    passed = '{"command":"ethos","verdict":"pass","required_gaps":[],"warnings":[]}'
    assert gate_runner.classify_action_result(exit_code=0, stdout=passed) == ("pass", ())
    blocked = (
        '{"command":"ethos","verdict":"block","state":"gapped",'
        '"diagnostics":["skip",{"severity":"warning","code":"warn"}]}'
    )
    verdict, diagnostics = gate_runner.classify_action_result(exit_code=0, stdout=blocked)
    assert verdict == "block"
    assert diagnostics[0]["required_gaps"] == ["ethos_result:warning:warn"]

    node = PlanNode(id="owner", kind="check", command=("provider", "ethos.fake:report"))
    gate = Gate(id="owner", kind="quality", providers=("ethos.fake:report",))
    monkeypatch.setattr(
        gate_runner.importlib,
        "import_module",
        lambda _name: SimpleNamespace(report=lambda _root: "not-a-mapping"),
    )
    result = gate_runner.LocalGateRunner().run(node, gate, root=tmp_path)
    assert (result.verdict, result.exit_code) == ("block", 1)
    assert result.diagnostics[0]["kind"] == "gate_provider_error"

    dry = gate_runner.DryRunRunner().run(node, gate, root=tmp_path)
    assert (dry.verdict, dry.exit_code) == ("unknown", None)


def test_workspace_public_missing_candidate_and_non_git(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(workspace, "_safe_ref", lambda *_args: "head")
    missing_branch = workspace.landing_readiness(
        tmp_path,
        branch="work/change",
        role="work_lane",
        candidate={"branch": "candidate/dev", "exists": False},
    )
    missing_tree = workspace.landing_readiness(
        tmp_path,
        branch="work/change",
        role="work_lane",
        candidate={"branch": "candidate/dev", "exists": True, "worktree_exists": False},
    )
    assert missing_branch["required_gaps"] == ["candidate_branch_missing"]
    assert missing_tree["required_gaps"] == ["candidate_worktree_missing"]

    monkeypatch.setattr(
        workspace,
        "git_stdout_checked",
        lambda *_args: (_ for _ in ()).throw(subprocess.CalledProcessError(128, "git")),
    )
    selected_runtime = object()
    observed: list[object] = []
    monkeypatch.setattr(
        workspace,
        "runtime_binding",
        lambda _root, *, selected_runtime=None: observed.append(selected_runtime) or {},
    )
    status = workspace.workspace_status(tmp_path, selected_runtime=selected_runtime)
    assert status["branch"] == "untracked"
    assert "git_repository_missing" in status["required_gaps"]
    assert status["landing_readiness"]["state"] == "not_work_lane"
    assert observed == [selected_runtime]


def test_landing_readiness_treats_unreadable_head_as_unknown(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        workspace,
        "git_stdout_checked",
        lambda *_args: (_ for _ in ()).throw(subprocess.CalledProcessError(128, "git")),
    )

    report = workspace.landing_readiness(
        tmp_path,
        branch="work/change",
        role="work_lane",
        candidate={
            "branch": "candidate/dev",
            "head": "a" * 40,
            "exists": True,
            "worktree_exists": True,
        },
    )

    assert report["head"] == ""
    assert report["state"] == "candidate_base_current"
