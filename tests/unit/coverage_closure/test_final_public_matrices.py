"""Compact public failure matrices for the final coverage closure."""

from __future__ import annotations

import ast
import subprocess
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.gates.runner as gate_runner
import ethos.adapters.repo.status.workspace as workspace
import ethos.repository.policy.layout.imports as layout_imports
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.branch.roles import branch_role_policy_from_text
from ethos.contracts.branch.roles import strict_branch_role_policy_from_text
from ethos.contracts.gates import Gate
from ethos.contracts.plan import PlanNode
from ethos.repository.policy.references.python_syntax import cyclopts_command_owners
from ethos.repository.policy.references.python_syntax import cyclopts_prefixes
from ethos.repository.policy.references.python_syntax import module_name

if TYPE_CHECKING:
    from pathlib import Path


STRICT = """[branch_roles]
release_branch = "main"
accepted_branch = "dev"
candidate_branch = "candidate/dev"
work_branch_prefix = "work/"
proposal_branch_prefix = "proposal/"
release_mirror = "independent"
canonical_sibling_worktrees = false
"""


@pytest.mark.parametrize(
    ("text", "error"),
    [
        ("[branch_roles\n", None),
        ("[other]\nvalue = 1\n", None),
        ("[branch_roles]\nunknown = 'x'\n", "unknown fields"),
    ],
)
def test_branch_role_lenient_parser_fail_closed(text: str, error: str | None) -> None:
    if error:
        with pytest.raises(ValueError, match=error):
            branch_role_policy_from_text(text)
    else:
        assert branch_role_policy_from_text(text) == BranchRolePolicy()


def test_branch_role_current_schema_maps_exactly() -> None:
    assert strict_branch_role_policy_from_text(STRICT) == BranchRolePolicy(
        canonical_sibling_worktrees=False
    )


@pytest.mark.parametrize(
    ("text", "error"),
    [
        (
            STRICT.replace('release_branch = "main"', 'release_branch = " main"'),
            "canonical strings",
        ),
        (
            STRICT.replace('release_mirror = "independent"', 'release_mirror = "mirror"'),
            "mirror is invalid",
        ),
        (
            STRICT.replace(
                "canonical_sibling_worktrees = false", 'canonical_sibling_worktrees = "false"'
            ),
            "must be boolean",
        ),
    ],
)
def test_branch_role_strict_value_contract(text: str, error: str) -> None:
    with pytest.raises(ValueError, match=error):
        strict_branch_role_policy_from_text(text)


def test_branch_role_lenient_value_defaults() -> None:
    report = branch_role_policy_from_text(
        "[branch_roles]\n"
        "release_branch = 1\n"
        "accepted_branch = ' '\n"
        "release_mirror = 'accepted_ff'\n"
    )
    assert (report.release_branch, report.accepted_branch, report.release_mirror) == (
        "main",
        "dev",
        "accepted_ff",
    )


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
    status = workspace.workspace_status(tmp_path)
    assert status["branch"] == "untracked"
    assert "git_repository_missing" in status["required_gaps"]
    assert status["landing_readiness"]["state"] == "not_work_lane"


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
