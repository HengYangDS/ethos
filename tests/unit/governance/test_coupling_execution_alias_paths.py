from __future__ import annotations

import ast
from typing import TYPE_CHECKING

import pytest

import ethos.repository.policy.coupling.execution.aliases.core as alias_resolution
from ethos.repository.policy.coupling.execution.audit import mandatory_executable_gaps
from ethos_core.contracts.registry.declarations import CouplingDeclaration
from ethos_core.contracts.registry.declarations import load_coupling_declaration

if TYPE_CHECKING:
    from pathlib import Path


_BINDING_ID = "work_lane_lifecycle_command_contract"


def _declaration(relative: str) -> CouplingDeclaration:
    payload = load_coupling_declaration().model_dump(mode="python", by_alias=True)
    binding = next(item for item in payload["binding"] if item["id"] == _BINDING_ID)
    binding["mandatory_paths"] = (relative,)
    binding["declared_executables"] = ("git",)
    binding["audit_root_bound"] = True
    return CouplingDeclaration.model_validate(payload)


def _write(root: Path, relative: str, source: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


@pytest.mark.parametrize(
    ("source", "line"),
    [
        (
            "import subprocess\n"
            "class Tool:\n"
            "    run = subprocess.run\n"
            "Tool.run(['tar', '--version'])\n",
            4,
        ),
        (
            "import subprocess\n"
            "class Tool:\n"
            "    process = subprocess\n"
            "Tool.process.run(['tar', '--version'])\n",
            4,
        ),
        (
            "import subprocess\n"
            "class Tool:\n"
            "    def configure(self):\n"
            "        self.run = subprocess.run\n"
            "tool = Tool()\n"
            "tool.configure()\n"
            "tool.run(['tar', '--version'])\n",
            7,
        ),
        (
            "import subprocess\nops = {'run': subprocess.run}\nops['run'](['tar', '--version'])\n",
            3,
        ),
        (
            "import subprocess\n"
            "class Tool:\n"
            "    run = subprocess.run\n"
            "getattr(Tool, 'run')(['tar', '--version'])\n",
            4,
        ),
        (
            "import subprocess\n"
            "class Tool:\n"
            "    process = subprocess\n"
            "getattr(Tool, 'process').run(['tar', '--version'])\n",
            4,
        ),
        (
            "import subprocess\n"
            "class Tool:\n"
            "    def configure(self):\n"
            "        self.run = subprocess.run\n"
            "tool = Tool()\n"
            "tool.configure()\n"
            "getattr(tool, 'run')(['tar', '--version'])\n",
            7,
        ),
        (
            "import subprocess\n"
            "class Tool:\n"
            "    run = subprocess.run\n"
            "invoke = Tool.run\n"
            "invoke(['tar', '--version'])\n",
            5,
        ),
        (
            "import subprocess\n"
            "class Tool:\n"
            "    process = subprocess\n"
            "proc = Tool.process\n"
            "proc.run(['tar', '--version'])\n",
            5,
        ),
        (
            "import subprocess\n"
            "class Tool:\n"
            "    run = subprocess.run\n"
            "ops = {'invoke': Tool.run}\n"
            "ops['invoke'](['tar', '--version'])\n",
            5,
        ),
    ],
)
def test_static_execution_alias_paths_are_audited(
    tmp_path: Path,
    source: str,
    line: int,
) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, source)

    assert mandatory_executable_gaps(tmp_path, _declaration(relative)) == [
        f"mandatory_executable_undeclared:{_BINDING_ID}:{relative}:{line}:tar"
    ]


@pytest.mark.parametrize(
    ("source", "line"),
    [
        (
            "import subprocess\n"
            "class Tool:\n"
            "    run = subprocess.run\n"
            "name = 'run'\n"
            "getattr(Tool, name)(['git', 'status'])\n",
            5,
        ),
        (
            "import subprocess\n"
            "ops = {'run': subprocess.run}\n"
            "key = 'run'\n"
            "ops[key](['git', 'status'])\n",
            4,
        ),
        (
            "import subprocess\n"
            "class Tool:\n"
            "    process = subprocess\n"
            "name = 'process'\n"
            "getattr(Tool, name).run(['git', 'status'])\n",
            5,
        ),
    ],
)
def test_dynamic_static_alias_paths_fail_closed(
    tmp_path: Path,
    source: str,
    line: int,
) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, source)

    assert mandatory_executable_gaps(tmp_path, _declaration(relative)) == [
        f"mandatory_executable_dynamic_argv0:{_BINDING_ID}:{relative}:{line}"
    ]


def test_function_local_unresolved_aliases_do_not_escape_their_scope(tmp_path: Path) -> None:
    relative = "mandatory/effect.py"
    _write(
        tmp_path,
        relative,
        "import subprocess\n"
        "class Tool:\n"
        "    run = subprocess.run\n"
        "def local():\n"
        "    invoke = alias\n"
        "alias = Tool.run\n"
        "def invoke(arguments):\n"
        "    return arguments\n"
        "invoke(['tar', '--version'])\n",
    )

    assert mandatory_executable_gaps(tmp_path, _declaration(relative)) == []


def test_class_local_unresolved_aliases_do_not_escape_their_scope(tmp_path: Path) -> None:
    relative = "mandatory/effect.py"
    _write(
        tmp_path,
        relative,
        "import subprocess\n"
        "class Tool:\n"
        "    run = subprocess.run\n"
        "class Holder:\n"
        "    invoke = alias\n"
        "alias = Tool.run\n"
        "def invoke(arguments):\n"
        "    return arguments\n"
        "invoke(['tar', '--version'])\n",
    )

    assert mandatory_executable_gaps(tmp_path, _declaration(relative)) == []


def test_deferred_functions_see_later_resolved_module_aliases(tmp_path: Path) -> None:
    relative = "mandatory/effect.py"
    _write(
        tmp_path,
        relative,
        "import subprocess\n"
        "class Tool:\n"
        "    run = subprocess.run\n"
        "def local():\n"
        "    invoke = alias\n"
        "    invoke(['tar', '--version'])\n"
        "alias = Tool.run\n",
    )

    assert mandatory_executable_gaps(tmp_path, _declaration(relative)) == [
        f"mandatory_executable_undeclared:{_BINDING_ID}:{relative}:6:tar"
    ]


@pytest.mark.parametrize(
    ("source", "line"),
    [
        (
            "import subprocess\nrun = {'run': subprocess.run}['run']\nrun(['tar', '--version'])\n",
            3,
        ),
        (
            "import subprocess\n"
            "ops = {'run': subprocess.run}\n"
            "ops.get('run')(['tar', '--version'])\n",
            3,
        ),
        (
            "import subprocess\n"
            "class Tool:\n"
            "    run = subprocess.run\n"
            "Tool.__dict__['run'](['tar', '--version'])\n",
            4,
        ),
        (
            "import subprocess\nread = getattr\nread(subprocess, 'run')(['tar', '--version'])\n",
            3,
        ),
    ],
)
def test_composed_static_execution_alias_paths_are_audited(
    tmp_path: Path,
    source: str,
    line: int,
) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, source)

    assert mandatory_executable_gaps(tmp_path, _declaration(relative)) == [
        f"mandatory_executable_undeclared:{_BINDING_ID}:{relative}:{line}:tar"
    ]


@pytest.mark.parametrize(
    ("source", "line"),
    [
        (
            "import subprocess\n"
            "ops = {'run': subprocess.run}\n"
            "key = 'run'\n"
            "ops.get(key)(['git', 'status'])\n",
            4,
        ),
        (
            "import subprocess\n"
            "class Tool:\n"
            "    run = subprocess.run\n"
            "key = 'run'\n"
            "Tool.__dict__[key](['git', 'status'])\n",
            5,
        ),
        (
            "import subprocess\n"
            "read = getattr\n"
            "name = 'run'\n"
            "read(subprocess, name)(['git', 'status'])\n",
            4,
        ),
    ],
)
def test_dynamic_composed_execution_alias_paths_fail_closed(
    tmp_path: Path,
    source: str,
    line: int,
) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, source)

    assert mandatory_executable_gaps(tmp_path, _declaration(relative)) == [
        f"mandatory_executable_dynamic_argv0:{_BINDING_ID}:{relative}:{line}"
    ]


@pytest.mark.parametrize(
    ("source", "line"),
    [
        (
            "import subprocess\n"
            "class Tool:\n"
            "    run = subprocess.run\n"
            "Tool.__dict__.get('run')(['tar', '--version'])\n",
            4,
        ),
        (
            "import subprocess\nsubprocess.__dict__['run'](['tar', '--version'])\n",
            2,
        ),
        (
            "import subprocess\nattrs = subprocess.__dict__\nattrs['run'](['tar', '--version'])\n",
            3,
        ),
        (
            "import subprocess\n{'run': subprocess.run}.get('run')(['tar', '--version'])\n",
            2,
        ),
        (
            "import subprocess\n"
            "{'op': {'run': subprocess.run}}['op']['run'](['tar', '--version'])\n",
            2,
        ),
        (
            "import subprocess\n"
            "ops = {'op': {'run': subprocess.run}}\n"
            "ops['op']['run'](['tar', '--version'])\n",
            3,
        ),
        (
            "import subprocess\nops = dict(run=subprocess.run)\nops['run'](['tar', '--version'])\n",
            3,
        ),
        (
            "from builtins import getattr as read\n"
            "import subprocess\n"
            "read(subprocess, 'run')(['tar', '--version'])\n",
            3,
        ),
    ],
)
def test_extended_static_execution_alias_paths_are_audited(
    tmp_path: Path,
    source: str,
    line: int,
) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, source)

    assert mandatory_executable_gaps(tmp_path, _declaration(relative)) == [
        f"mandatory_executable_undeclared:{_BINDING_ID}:{relative}:{line}:tar"
    ]


@pytest.mark.parametrize(
    ("source", "line"),
    [
        (
            "import subprocess\n"
            "class Tool:\n"
            "    run = subprocess.run\n"
            "key = 'run'\n"
            "Tool.__dict__.get(key)(['git', 'status'])\n",
            5,
        ),
        (
            "import subprocess\nkey = 'run'\nsubprocess.__dict__[key](['git', 'status'])\n",
            3,
        ),
        (
            "import subprocess\nkey = 'run'\n{'run': subprocess.run}.get(key)(['git', 'status'])\n",
            3,
        ),
        (
            "import subprocess\nkey = 'run'\n{'run': subprocess.run}[key](['git', 'status'])\n",
            3,
        ),
    ],
)
def test_extended_dynamic_execution_alias_paths_fail_closed(
    tmp_path: Path,
    source: str,
    line: int,
) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, source)

    assert mandatory_executable_gaps(tmp_path, _declaration(relative)) == [
        f"mandatory_executable_dynamic_argv0:{_BINDING_ID}:{relative}:{line}"
    ]


@pytest.mark.parametrize(
    "source",
    [
        "import subprocess\n"
        "invoke = subprocess.run\n"
        "invoke = lambda arguments: arguments\n"
        "invoke(['tar', '--version'])\n",
        "import subprocess\n"
        "def getattr(object_: object, name: str) -> object:\n"
        "    return object_\n"
        "getattr(subprocess, 'run')(['tar', '--version'])\n",
    ],
)
def test_non_execution_rebinding_does_not_create_a_spurious_gap(
    tmp_path: Path,
    source: str,
) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, source)

    assert mandatory_executable_gaps(tmp_path, _declaration(relative)) == []


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            "import subprocess as process\n"
            "def execute():\n"
            "    process.run(['tar', '--version'])\n"
            "execute()\n"
            "process = object()\n",
            [f"mandatory_executable_undeclared:{_BINDING_ID}:mandatory/effect.py:3:tar"],
        ),
        (
            "import subprocess as process\n"
            "def execute():\n"
            "    process.run(['tar', '--version'])\n"
            "process = object()\n"
            "execute()\n",
            [],
        ),
        (
            "import os\n"
            "import subprocess\n"
            "process = os\n"
            "def execute():\n"
            "    process.run(['tar', '--version'])\n"
            "execute()\n"
            "process = subprocess\n"
            "execute()\n"
            "process = os\n",
            [f"mandatory_executable_undeclared:{_BINDING_ID}:mandatory/effect.py:5:tar"],
        ),
    ],
)
def test_direct_deferred_calls_use_their_call_site_alias_state(
    tmp_path: Path,
    source: str,
    expected: list[str],
) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, source)

    assert mandatory_executable_gaps(tmp_path, _declaration(relative)) == expected


@pytest.mark.parametrize(
    ("source", "line"),
    [
        (
            "import subprocess\n"
            "class Tool:\n"
            "    read = getattr\n"
            "Tool.read(subprocess, 'run')(['tar', '--version'])\n",
            4,
        ),
        (
            "import subprocess\n"
            "ops = {'read': getattr}\n"
            "ops['read'](subprocess, 'run')(['tar', '--version'])\n",
            3,
        ),
    ],
)
def test_static_getattr_aliases_do_not_report_the_getter_call_itself(
    tmp_path: Path,
    source: str,
    line: int,
) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, source)

    assert mandatory_executable_gaps(tmp_path, _declaration(relative)) == [
        f"mandatory_executable_undeclared:{_BINDING_ID}:{relative}:{line}:tar"
    ]


@pytest.mark.parametrize(
    "source",
    [
        "import subprocess\n"
        "class Tool:\n"
        "    run = subprocess.run\n"
        "Tool.run = lambda arguments: arguments\n"
        "Tool.run(['tar', '--version'])\n",
        "import subprocess\n"
        "ops = {'run': subprocess.run}\n"
        "ops['run'] = lambda arguments: arguments\n"
        "ops['run'](['tar', '--version'])\n",
    ],
)
def test_static_member_rebinding_does_not_create_a_spurious_gap(
    tmp_path: Path,
    source: str,
) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, source)

    assert mandatory_executable_gaps(tmp_path, _declaration(relative)) == []


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            "from subprocess import *\nrun(['tar', '--version'])\n",
            [f"mandatory_executable_undeclared:{_BINDING_ID}:mandatory/effect.py:2:tar"],
        ),
        (
            "import os.path\nos.system('git status')\n",
            [f"mandatory_executable_shell_true:{_BINDING_ID}:mandatory/effect.py:2"],
        ),
        (
            "import asyncio.tasks\nasyncio.create_subprocess_exec('tar', '--version')\n",
            [f"mandatory_executable_undeclared:{_BINDING_ID}:mandatory/effect.py:2:tar"],
        ),
    ],
)
def test_standard_import_forms_preserve_known_execution_bindings(
    tmp_path: Path,
    source: str,
    expected: list[str],
) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, source)

    assert mandatory_executable_gaps(tmp_path, _declaration(relative)) == expected


@pytest.mark.parametrize(
    "source",
    [
        "import os.path as path\npath.system('git status')\n",
        "import asyncio.tasks as tasks\ntasks.create_subprocess_exec('tar', '--version')\n",
    ],
)
def test_aliased_nonexecution_dotted_modules_are_not_collapsed_to_their_root(
    tmp_path: Path,
    source: str,
) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, source)

    assert mandatory_executable_gaps(tmp_path, _declaration(relative)) == []


@pytest.mark.parametrize(
    "source",
    [
        "import subprocess\n"
        "class Tool:\n"
        "    def configure(self):\n"
        "        self.run = subprocess.run\n"
        "class Other:\n"
        "    def run(self, arguments):\n"
        "        return arguments\n"
        "other = Other()\n"
        "other.run(['tar', '--version'])\n",
        "import subprocess\n"
        "class Tool:\n"
        "    def configure(self):\n"
        "        self.run = subprocess.run\n"
        "tool = Tool()\n"
        "tool.run(['tar', '--version'])\n",
    ],
)
def test_instance_effects_require_the_known_configuring_method_call(
    tmp_path: Path,
    source: str,
) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, source)

    assert mandatory_executable_gaps(tmp_path, _declaration(relative)) == []


def test_module_delete_of_getattr_reveals_the_builtin_again(tmp_path: Path) -> None:
    relative = "mandatory/effect.py"
    _write(
        tmp_path,
        relative,
        "import subprocess\n"
        "getattr = lambda *arguments: None\n"
        "del getattr\n"
        "getattr(subprocess, 'run')(['tar', '--version'])\n",
    )

    assert mandatory_executable_gaps(tmp_path, _declaration(relative)) == [
        f"mandatory_executable_undeclared:{_BINDING_ID}:{relative}:4:tar"
    ]


@pytest.mark.parametrize(
    ("source", "line"),
    [
        (
            "import builtins\n"
            "import subprocess\n"
            "builtins.getattr(subprocess, 'run')(['tar', '--version'])\n",
            3,
        ),
        (
            "import builtins as functions\n"
            "import subprocess\n"
            "functions.getattr(subprocess, 'run')(['tar', '--version'])\n",
            3,
        ),
        (
            "import asyncio\n"
            "getattr(asyncio, 'subprocess').create_subprocess_exec('tar', '--version')\n",
            2,
        ),
        (
            "import asyncio\n"
            "getattr(asyncio.__dict__, 'subprocess').create_subprocess_exec(\n"
            "    'tar', '--version'\n"
            ")\n",
            2,
        ),
        (
            "import asyncio\n"
            "process = asyncio.__dict__['subprocess']\n"
            "process.create_subprocess_exec('tar', '--version')\n",
            3,
        ),
    ],
)
def test_builtin_and_module_getattr_paths_are_audited(
    tmp_path: Path,
    source: str,
    line: int,
) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, source)

    assert mandatory_executable_gaps(tmp_path, _declaration(relative)) == [
        f"mandatory_executable_undeclared:{_BINDING_ID}:{relative}:{line}:tar"
    ]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            "from os.path import *\n"
            "import subprocess\n"
            "getattr()(['git', 'status'])\n"
            "getattr(subprocess)(['git', 'status'])\n"
            "{'run': subprocess.run}.get()(['git', 'status'])\n"
            "missing = getattr()\n"
            "missing.create_subprocess_exec('git', 'status')\n"
            "missing = {}.get()\n"
            "missing.create_subprocess_exec('git', 'status')\n"
            "unknown = object()\n"
            "name = 'run'\n"
            "getattr(unknown, name)(['git', 'status'])\n"
            "module = getattr(unknown, name)\n"
            "module.create_subprocess_exec('git', 'status')\n",
            [f"mandatory_executable_dynamic_argv0:{_BINDING_ID}:mandatory/effect.py:4"],
        ),
        (
            "import asyncio\n"
            "direct = asyncio.__dict__['subprocess']\n"
            "direct.create_subprocess_exec('tar', '--version')\n"
            "via_get = asyncio.__dict__.get('subprocess')\n"
            "via_get.create_subprocess_exec('git', 'status')\n"
            "name = 'subprocess'\n"
            "dynamic = asyncio.__dict__[name]\n"
            "dynamic.create_subprocess_exec('git', 'status')\n"
            "unknown = object.__dict__[name]\n"
            "unknown.create_subprocess_exec('git', 'status')\n",
            [
                f"mandatory_executable_dynamic_argv0:{_BINDING_ID}:mandatory/effect.py:8",
                f"mandatory_executable_undeclared:{_BINDING_ID}:mandatory/effect.py:3:tar",
            ],
        ),
        (
            "import asyncio\n"
            "key = 'subprocess'\n"
            "[asyncio][key].create_subprocess_exec('git', 'status')\n"
            "ops = {'child': asyncio}\n"
            "key = 'child'\n"
            "ops[key].create_subprocess_exec('git', 'status')\n",
            [
                f"mandatory_executable_dynamic_argv0:{_BINDING_ID}:mandatory/effect.py:3",
                f"mandatory_executable_dynamic_argv0:{_BINDING_ID}:mandatory/effect.py:6",
            ],
        ),
        (
            "import subprocess\n"
            "[{'skip': None, 'run': subprocess.run}['run']][0](['tar', '--version'])\n"
            "key = 'run'\n"
            "({'run': {'run': subprocess.run}}[key])['run'](['git', 'status'])\n",
            [f"mandatory_executable_undeclared:{_BINDING_ID}:mandatory/effect.py:2:tar"],
        ),
    ],
)
def test_dynamic_and_literal_container_alias_boundaries_are_audited(
    tmp_path: Path,
    source: str,
    expected: list[str],
) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, source)

    assert mandatory_executable_gaps(tmp_path, _declaration(relative)) == expected


def test_dunder_dict_module_aliases_precede_canonical_module_lookup() -> None:
    expression = ast.parse("owner.__dict__['subprocess']").body[0]
    assert isinstance(expression, ast.Expr)

    assert alias_resolution.module_reference(
        expression.value,
        {"owner.subprocess": frozenset({"asyncio"})},
    ) == frozenset({"asyncio"})
