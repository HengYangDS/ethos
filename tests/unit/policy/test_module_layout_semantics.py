"""Enforce semantic package ownership across tracked and candidate source."""

from __future__ import annotations

import subprocess

import pytest

import ethos.repository.policy.layout.imports as layout_imports
from ethos.adapters.gates.tool import module_layout_gate_report
from ethos.repository.policy.layout.facades import facade_findings
from ethos.repository.policy.layout.naming import ambiguous_module_findings
from ethos.repository.policy.layout.naming import multiple_command_owner_findings
from ethos.repository.policy.layout.policy import empty_package_findings
from ethos.repository.policy.layout.policy import package_python_files
from ethos.repository.policy.layout.policy import semantic_python_files
from ethos.repository.policy.layout.report import module_layout_report
from tests.support.governed_repository import write_file


def test_module_facade_with_all_is_still_blocked(tmp_path) -> None:
    write_file(
        tmp_path / "src/ethos/legacy.py",
        'from ethos.result import EthosResult\n\n__all__ = ["EthosResult"]\n',
    )

    findings = facade_findings(tmp_path, {"semantic_paths": ["."]})["module_facade_findings"]
    assert findings[0]["reasons"] == ["import_only"]


def test_empty_package_shell_without_consumers_is_blocked(tmp_path) -> None:
    write_file(tmp_path / "src/ethos/empty/__init__.py", '"""Marker only."""\n')

    assert empty_package_findings(tmp_path, {"semantic_paths": ["."]}) == [
        {
            "gap": "module_layout_empty_package:src/ethos/empty",
            "path": "src/ethos/empty",
            "module": "ethos.empty",
        }
    ]


def test_empty_package_with_a_public_import_boundary_is_retained(tmp_path) -> None:
    write_file(tmp_path / "src/ethos/empty/__init__.py", '"""Public namespace."""\n')
    write_file(tmp_path / "src/ethos/consumer.py", "import ethos.empty\n")

    assert empty_package_findings(tmp_path, {"semantic_paths": ["."]}) == []


def test_ambiguous_module_name_is_always_blocked(tmp_path) -> None:
    write_file(tmp_path / "src/ethos/domain/core.py", "def decide():\n    return True\n")
    policy = {"paths": ["src/ethos"], "ambiguous_module_names": ["core"]}

    assert ambiguous_module_findings(tmp_path, policy) == [
        {
            "gap": "module_layout_ambiguous_module:src/ethos/domain/core.py",
            "path": "src/ethos/domain/core.py",
            "module": "core",
            "ambiguous_tokens": ["core"],
        }
    ]


def test_ambiguous_module_name_tokens_cannot_hide_in_compounds(tmp_path) -> None:
    write_file(tmp_path / "tests/support/contract_helpers.py", "VALUE = 1\n")
    policy = {"semantic_paths": ["tests"], "ambiguous_module_names": ["helpers"]}

    assert ambiguous_module_findings(tmp_path, policy) == [
        {
            "gap": "module_layout_ambiguous_module:tests/support/contract_helpers.py",
            "path": "tests/support/contract_helpers.py",
            "module": "contract_helpers",
            "ambiguous_tokens": ["helpers"],
        }
    ]


def test_role_contract_cannot_exempt_ambiguous_module_name(tmp_path) -> None:
    relative = "src/ethos/domain/core.py"
    write_file(tmp_path / relative, "def decide():\n    return True\n")
    policy = {
        "paths": ["src/ethos"],
        "ambiguous_module_names": ["core"],
        "ambiguous_module_roles": [
            {
                "path": relative,
                "role": "kernel",
                "concept": "pure transition decision",
                "authority_refs": ["docs/architecture/transition-plan.md"],
                "public_symbols": ["decide"],
                "max_eloc": 4,
                "allowed_import_roots": ["ethos.contracts"],
            }
        ],
    }

    assert ambiguous_module_findings(tmp_path, policy)[0]["path"] == relative


def test_surface_core_command_and_multiple_apps_are_blocked(tmp_path) -> None:
    relative = "src/ethos/surface/cli/lane/core.py"
    write_file(
        tmp_path / relative,
        """@lane_app.command()
def status():
    pass

@retire_app.command()
def retire():
    pass
""",
    )
    policy = {"paths": ["src/ethos"]}

    assert ambiguous_module_findings(tmp_path, policy)[0]["path"] == relative
    assert multiple_command_owner_findings(tmp_path, policy)[0]["owners"] == [
        "lane_app",
        "retire_app",
    ]


def test_semantic_scope_covers_source_tests_tools_and_agent_scripts(tmp_path) -> None:
    expected = {
        ".agents/skills/sample/scripts/check.py",
        "src/ethos/domain/model.py",
        "tests/unit/test_model.py",
        "tools/ci/check.py",
    }
    for relative in expected:
        write_file(tmp_path / relative, "VALUE = 1\n")
    policy = {
        "semantic_paths": [".agents/skills", "src/ethos", "tests", "tools"],
        "package_paths": ["src/ethos"],
    }

    assert {
        path.relative_to(tmp_path).as_posix() for path in semantic_python_files(tmp_path, policy)
    } == expected
    assert {
        path.relative_to(tmp_path).as_posix() for path in package_python_files(tmp_path, policy)
    } == {"src/ethos/domain/model.py"}


def test_semantic_scope_includes_untracked_and_excludes_deleted_python(tmp_path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    tracked = write_file(tmp_path / "src/ethos/model.py", "VALUE = 1\n")
    deleted = write_file(tmp_path / "src/ethos/deleted.py", "VALUE = 1\n")
    subprocess.run(["git", "add", tracked, deleted], cwd=tmp_path, check=True)
    deleted.unlink()
    write_file(tmp_path / "tools/core.py", "VALUE = 1\n")

    files = {
        path.relative_to(tmp_path).as_posix()
        for path in semantic_python_files(tmp_path, {"semantic_paths": ["."]})
    }

    assert files == {"src/ethos/model.py", "tools/core.py"}


def test_module_layout_gate_includes_untracked_and_excludes_ignored_python(tmp_path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    tracked = write_file(tmp_path / "src/ethos/model.py", "VALUE = 1\n")
    write_file(tmp_path / ".gitignore", "tools/ignored.py\n")
    subprocess.run(["git", "add", tracked, ".gitignore"], cwd=tmp_path, check=True)
    write_file(tmp_path / "tools/core.py", "VALUE = 1\n")
    write_file(tmp_path / "tools/ignored.py", "VALUE = 1\n")

    report = module_layout_gate_report(tmp_path)

    assert report["verdict"] == "block"
    assert "ok" not in report
    assert report["required_gaps"] == ["module_layout_ambiguous_module:tools/core.py"]


def test_ambiguous_names_are_blocked_in_every_owned_python_carrier(tmp_path) -> None:
    for relative in (
        ".agents/skills/sample/scripts/helpers.py",
        "src/ethos/domain/core.py",
        "tests/support/common.py",
        "tools/ci/utils.py",
    ):
        write_file(tmp_path / relative, "VALUE = 1\n")
    policy = {
        "semantic_paths": [".agents/skills", "src/ethos", "tests", "tools"],
        "package_paths": ["src/ethos"],
        "ambiguous_module_names": ["common", "core", "helpers", "utils"],
    }

    assert {finding["path"] for finding in ambiguous_module_findings(tmp_path, policy)} == {
        ".agents/skills/sample/scripts/helpers.py",
        "src/ethos/domain/core.py",
        "tests/support/common.py",
        "tools/ci/utils.py",
    }


def test_native_test_and_tool_names_are_not_treated_as_ambiguous(tmp_path) -> None:
    for relative in (
        "tests/unit/test_change_report.py",
        "tests/unit/test_change_index.py",
        "tests/unit/test_change_native.py",
        "tools/ci/change_report.py",
        "tools/ci/change_index.py",
        "tools/ci/change_native.py",
    ):
        write_file(tmp_path / relative, "VALUE = 1\n")
    policy = {
        "semantic_paths": ["src/ethos", "tests", "tools"],
        "package_paths": ["src/ethos"],
        "ambiguous_module_names": ["common", "core", "helpers", "utils"],
    }

    assert ambiguous_module_findings(tmp_path, policy) == []


@pytest.mark.parametrize(
    "relative",
    [
        "src/ethos/planning.py",
        "tests/test_planning.py",
        "tools/planning.py",
        ".agents/skills/sample/scripts/planning.py",
    ],
)
def test_code_entities_use_semantic_names_in_every_owned_carrier(tmp_path, relative) -> None:
    write_file(
        tmp_path / relative,
        "class PlanV2: pass\ndef compile_v3(v4): return v4\nplan_v1 = PlanV2()\n",
    )

    report = module_layout_report(tmp_path)

    assert report["verdict"] == "block"
    assert {finding["identifier"] for finding in report["identifier_naming_findings"]} == {
        "PlanV2",
        "compile_v3",
        "v4",
        "plan_v1",
    }


def test_protocol_values_do_not_define_numbered_code_entities(tmp_path) -> None:
    write_file(
        tmp_path / "src/ethos/planning.py",
        'protocol_version = "schema-v2"\n'
        'ipv4 = "192.0.2.1"\n'
        "class Revision: pass\n"
        "def compile_plan(current): return current\n",
    )

    assert module_layout_report(tmp_path)["verdict"] == "pass"


def test_import_policy_finds_package_root_and_private_imports(tmp_path, monkeypatch) -> None:
    sources = {
        "__init__.py": "",
        "tools.py": "VALUE = 1\n",
        "src/pkg/__init__.py": "",
        "src/pkg/child.py": "VALUE = 1\n",
        "src/pkg/consumer.py": (
            "from pkg import *\n"
            "from pkg import child as _hidden\n"
            "from pkg import child, missing\n"
            "from pkg.child import *\n"
            "from pkg.child import __dunder__, _private, public\n"
        ),
    }
    paths = tuple(write_file(tmp_path / path, source) for path, source in sources.items())
    monkeypatch.setattr(layout_imports, "package_python_files", lambda *_a, **_k: paths)
    monkeypatch.setattr(layout_imports, "semantic_python_files", lambda *_a, **_k: paths)
    roots = layout_imports.package_root_submodule_import_findings(tmp_path, {}, paths)
    private = layout_imports.private_import_findings(tmp_path, {}, paths)
    assert [item["module"] for item in roots] == ["pkg.child"]
    assert [item["name"] for item in private] == ["_private"]


@pytest.mark.parametrize(
    ("statement", "owner"),
    [
        ("from ethos.facade import Result", "ethos.api"),
        ("from ethos.facade import codec", "json"),
        ("from ethos.facade import VALUE", None),
        ("from ethos.facade import Fallback", None),
        ("from ethos.api import Result", None),
        ("from ethos import facade", None),
        ("from yaml import safe_load", None),
    ],
)
def test_import_policy_names_the_defining_module_of_an_indirect_import(
    tmp_path, statement, owner
) -> None:
    write_file(tmp_path / "src/ethos/api.py", "class Result:\n    pass\n")
    write_file(
        tmp_path / "src/ethos/facade.py",
        "import json as codec\nfrom ethos.api import Result\nfrom ...... import lost\n"
        "try:\n    from ethos.api import Fallback\nexcept ImportError:\n    Fallback = None\n"
        "VALUE = Result\n",
    )
    write_file(tmp_path / "src/ethos/use.py", statement + "\n")

    findings = layout_imports.private_import_findings(tmp_path, {"semantic_paths": ["src"]})

    assert [item["module"] for item in findings if "indirect" in str(item["gap"])] == (
        [owner] if owner else []
    )


@pytest.mark.parametrize(
    ("statement", "gap"),
    [
        ("from ethos.api import Result as Stable", "import_rename:{}:ethos.api.Result->Stable"),
        ("from ethos.facade import Result", "indirect_import:{}:ethos.facade->Result"),
        ("from ethos.api import Result as Base\nclass Result(Base):\n    pass", ""),
        ("from ethos.api import Result", ""),
    ],
)
def test_public_layout_gate_refuses_renaming_aliases_and_indirect_imports(tmp_path, statement, gap):
    """An import names a symbol canonically at its definer unless a collision needs `as`."""
    write_file(tmp_path / "src/ethos/api.py", "class Result:\n    pass\n")
    write_file(tmp_path / "src/ethos/facade.py", "from ethos.api import Result\n\nVALUE = Result\n")
    write_file(tmp_path / "src/ethos/use.py", statement + "\nprint('consumer')\n")

    report = module_layout_report(tmp_path)

    found = [*report["private_alias_findings"], *report["private_import_findings"]]
    expected = [f"module_layout_{gap.format('src/ethos/use.py')}"] * bool(gap)
    assert report["required_gaps"] == expected
    assert [(item["path"], item["line"], item["module"]) for item in found] == [
        ("src/ethos/use.py", 1, "ethos.api")
    ] * bool(gap)


@pytest.mark.parametrize(
    ("consumer", "statement", "blocked"),
    [
        ("src/ethos/other/use.py", "from ethos.owner._engine import run", True),
        ("src/ethos/other/use.py", "import ethos.owner._engine as engine", True),
        ("src/ethos/other/use.py", "from ethos.owner import _engine as engine", True),
        ("src/ethos/other/use.py", "from ..owner._engine import run", True),
        ("tests/test_use.py", "from ethos.owner._engine import run", True),
        ("tools/check.py", "import ethos.owner._engine", True),
        ("src/ethos/owner_extra/use.py", "from ethos.owner._engine import run", True),
        ("src/ethos/owner/child/use.py", "from ethos.owner._engine import run", True),
        ("src/ethos/owner/use.py", "from ethos.owner._engine import run", False),
        ("src/ethos/owner/use.py", "import ethos.owner._engine as engine", False),
        ("src/ethos/owner/use.py", "from ._engine import run", False),
        ("src/ethos/other/use.py", "from ethos.owner.api import run", False),
        ("src/ethos/other/use.py", "from ethos.owner._internal.api import run", True),
        ("src/ethos/owner/_internal/use.py", "from ethos.owner._internal.api import run", False),
        (
            "src/ethos/owner/_internal/deep/use.py",
            "from ethos.owner._internal.api import run",
            False,
        ),
        ("src/ethos/other/use.py", "from ethos.owner.api import _hidden as hidden", True),
        ("src/ethos/other/use.py", "from ..owner.api import _hidden", True),
        ("src/ethos/other/use.py", "from ethos.owner.api import __hidden", True),
        ("src/ethos/other/use.py", "from ethos.owner.api import __version__", False),
    ],
)
def test_public_layout_gate_enforces_private_ownership(tmp_path, consumer, statement, blocked):
    """Import spelling cannot cross ownership, while internal cooperation stays legal."""
    write_file(tmp_path / "src/ethos/owner/_engine.py", "def run():\n    return 1\n")
    write_file(tmp_path / "src/ethos/owner/api.py", "def run():\n    return 1\n")
    write_file(tmp_path / "src/ethos/owner/_internal/api.py", "def run():\n    return 1\n")
    write_file(tmp_path / consumer, statement + "\nprint('consumer')\n")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)

    report = module_layout_gate_report(tmp_path)

    gaps = report["required_gaps"]
    assert any("private" in gap for gap in gaps) is blocked, report
    assert report["verdict"] == ("block" if blocked else "pass"), report
