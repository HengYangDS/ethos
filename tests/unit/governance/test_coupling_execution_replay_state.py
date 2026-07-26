from __future__ import annotations

import ast
from typing import TYPE_CHECKING

import pytest

import ethos.repository.policy.coupling.execution.analysis.replay as replay
from ethos.repository.policy.coupling.execution.audit import mandatory_executable_gaps
from ethos.repository.policy.coupling.execution.collector import _ExecutionCallCollector
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
            "def configure():\n"
            "    global process\n"
            "    process = subprocess\n"
            "configure()\n"
            "process.run(['tar', '--version'])\n",
            6,
        ),
        (
            "import subprocess\n"
            "def outer():\n"
            "    process = object()\n"
            "    def configure():\n"
            "        nonlocal process\n"
            "        process = subprocess\n"
            "    configure()\n"
            "    process.run(['tar', '--version'])\n"
            "outer()\n",
            8,
        ),
    ],
)
def test_direct_callable_scope_writes_reach_their_declared_owner(
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
            "import subprocess as process\n"
            "ops = {'run': lambda: process.run(['tar', '--version'])}\n"
            "ops['run']()\n"
            "process = object()\n",
            2,
        ),
        (
            "import subprocess as process\n"
            "def invoke():\n"
            "    process.run(['tar', '--version'])\n"
            "ops = {'run': invoke}\n"
            "ops['run']()\n"
            "process = object()\n",
            3,
        ),
        (
            "import subprocess as process\n"
            "class Ops:\n"
            "    pass\n"
            "Ops.run = lambda: process.run(['tar', '--version'])\n"
            "Ops.run()\n"
            "process = object()\n",
            4,
        ),
        (
            "import subprocess as process\n"
            "class Ops:\n"
            "    pass\n"
            "def invoke():\n"
            "    process.run(['tar', '--version'])\n"
            "Ops.run = invoke\n"
            "Ops.run()\n"
            "process = object()\n",
            5,
        ),
    ],
)
def test_static_user_callable_aliases_replay_at_their_early_call_site(
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
            "import subprocess as process\n"
            "if condition:\n"
            "    def invoke():\n"
            "        process.run(['tar', '--version'])\n"
            "else:\n"
            "    def invoke():\n"
            "        return None\n"
            "invoke()\n"
            "process = object()\n",
            4,
        ),
        (
            "import subprocess as process\n"
            "if condition:\n"
            "    def invoke():\n"
            "        return None\n"
            "else:\n"
            "    def invoke():\n"
            "        process.run(['tar', '--version'])\n"
            "invoke()\n"
            "process = object()\n",
            7,
        ),
        (
            "import subprocess as process\n"
            "if condition:\n"
            "    invoke = lambda: process.run(['tar', '--version'])\n"
            "else:\n"
            "    invoke = lambda: None\n"
            "invoke()\n"
            "process = object()\n",
            3,
        ),
        (
            "import subprocess as process\n"
            "if condition:\n"
            "    invoke = lambda: None\n"
            "else:\n"
            "    invoke = lambda: process.run(['tar', '--version'])\n"
            "invoke()\n"
            "process = object()\n",
            5,
        ),
        (
            "import subprocess as process\n"
            "if condition:\n"
            "    class Tool:\n"
            "        def invoke(self):\n"
            "            process.run(['tar', '--version'])\n"
            "else:\n"
            "    class Tool:\n"
            "        def invoke(self):\n"
            "            return None\n"
            "tool = Tool()\n"
            "tool.invoke()\n"
            "process = object()\n",
            5,
        ),
        (
            "import subprocess as process\n"
            "if condition:\n"
            "    class Tool:\n"
            "        def configure(self):\n"
            "            self.run = process.run\n"
            "else:\n"
            "    class Tool:\n"
            "        def configure(self):\n"
            "            self.run = lambda arguments: arguments\n"
            "tool = Tool()\n"
            "tool.configure()\n"
            "tool.run(['tar', '--version'])\n"
            "process = object()\n",
            12,
        ),
        (
            "import subprocess as process\n"
            "try:\n"
            "    def invoke():\n"
            "        process.run(['tar', '--version'])\n"
            "except Exception:\n"
            "    def invoke():\n"
            "        return None\n"
            "invoke()\n"
            "process = object()\n",
            4,
        ),
        (
            "import subprocess as process\n"
            "match value:\n"
            "    case 1:\n"
            "        def invoke():\n"
            "            return None\n"
            "    case _:\n"
            "        def invoke():\n"
            "            process.run(['tar', '--version'])\n"
            "invoke()\n"
            "process = object()\n",
            8,
        ),
    ],
)
def test_branch_local_replay_state_keeps_every_possible_execution_path(
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
        (
            "def outer():\n"
            "    import subprocess as process\n"
            "    def configure():\n"
            "        nonlocal process\n"
            "        process = object()\n"
            "    configure()\n"
            "    process.run(['tar', '--version'])\n"
            "outer()\n"
        ),
        (
            "def outer():\n"
            "    import subprocess as process\n"
            "    def configure():\n"
            "        nonlocal process\n"
            "        del process\n"
            "    configure()\n"
            "    process.run(['tar', '--version'])\n"
            "outer()\n"
        ),
    ],
)
def test_repeated_replay_preserves_nonlocal_rebind_or_delete(
    tmp_path: Path,
    source: str,
) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, source)

    assert mandatory_executable_gaps(tmp_path, _declaration(relative)) == []


@pytest.mark.parametrize(
    ("source", "line"),
    [
        (
            "import subprocess as process\n"
            "def invoke():\n"
            "    process.run(['tar', '--version'])\n"
            "def configure():\n"
            "    global target\n"
            "    target = invoke\n"
            "configure()\n"
            "target()\n"
            "process = object()\n",
            3,
        ),
        (
            "def outer():\n"
            "    import subprocess as process\n"
            "    def invoke():\n"
            "        process.run(['tar', '--version'])\n"
            "    target = lambda: None\n"
            "    def configure():\n"
            "        nonlocal target\n"
            "        target = invoke\n"
            "    configure()\n"
            "    target()\n"
            "    process = object()\n"
            "outer()\n",
            4,
        ),
        (
            "import subprocess as process\n"
            "def invoke():\n"
            "    process.run(['tar', '--version'])\n"
            "ops = {}\n"
            "def configure():\n"
            "    ops['run'] = invoke\n"
            "configure()\n"
            "ops['run']()\n"
            "process = object()\n",
            3,
        ),
        (
            "import subprocess as process\n"
            "def invoke():\n"
            "    process.run(['tar', '--version'])\n"
            "class Ops:\n"
            "    pass\n"
            "def configure():\n"
            "    Ops.run = invoke\n"
            "configure()\n"
            "Ops.run()\n"
            "process = object()\n",
            3,
        ),
        (
            "import subprocess as process\n"
            "def invoke():\n"
            "    process.run(['tar', '--version'])\n"
            "class Ops:\n"
            "    pass\n"
            "ops = Ops()\n"
            "def configure():\n"
            "    ops.run = invoke\n"
            "configure()\n"
            "ops.run()\n"
            "process = object()\n",
            3,
        ),
    ],
)
def test_helper_external_callable_writes_replay_at_later_call_sites(
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
        (
            "import subprocess as process\n"
            "def invoke():\n"
            "    process.run(['tar', '--version'])\n"
            "target = invoke\n"
            "def configure():\n"
            "    global target\n"
            "    target = lambda: None\n"
            "configure()\n"
            "target()\n"
            "process = object()\n"
        ),
        (
            "def outer():\n"
            "    import subprocess as process\n"
            "    def invoke():\n"
            "        process.run(['tar', '--version'])\n"
            "    target = invoke\n"
            "    def configure():\n"
            "        nonlocal target\n"
            "        target = lambda: None\n"
            "    configure()\n"
            "    target()\n"
            "    process = object()\n"
            "outer()\n"
        ),
        (
            "import subprocess as process\n"
            "def invoke():\n"
            "    process.run(['tar', '--version'])\n"
            "ops = {'run': invoke}\n"
            "def configure():\n"
            "    ops['run'] = lambda: None\n"
            "configure()\n"
            "ops['run']()\n"
            "process = object()\n"
        ),
        (
            "import subprocess as process\n"
            "def invoke():\n"
            "    process.run(['tar', '--version'])\n"
            "class Ops:\n"
            "    pass\n"
            "Ops.run = invoke\n"
            "def configure():\n"
            "    Ops.run = lambda: None\n"
            "configure()\n"
            "Ops.run()\n"
            "process = object()\n"
        ),
        (
            "import subprocess as process\n"
            "def invoke():\n"
            "    process.run(['tar', '--version'])\n"
            "class Ops:\n"
            "    pass\n"
            "ops = Ops()\n"
            "ops.run = invoke\n"
            "def configure():\n"
            "    ops.run = lambda: None\n"
            "configure()\n"
            "ops.run()\n"
            "process = object()\n"
        ),
    ],
)
def test_helper_external_callable_rebind_clears_old_candidate(
    tmp_path: Path,
    source: str,
) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, source)

    assert mandatory_executable_gaps(tmp_path, _declaration(relative)) == []


@pytest.mark.parametrize(
    "source",
    [
        (
            "import subprocess\n"
            "ops = {'run': subprocess.run}\n"
            "def configure():\n"
            "    ops['run'] = lambda argv: argv\n"
            "configure()\n"
            "ops['run'](['tar', '--version'])\n"
        ),
        (
            "import subprocess\n"
            "class Ops:\n"
            "    pass\n"
            "Ops.run = subprocess.run\n"
            "def configure():\n"
            "    Ops.run = lambda argv: argv\n"
            "configure()\n"
            "Ops.run(['tar', '--version'])\n"
        ),
        (
            "import subprocess\n"
            "class Ops:\n"
            "    pass\n"
            "ops = Ops()\n"
            "ops.run = subprocess.run\n"
            "def configure():\n"
            "    ops.run = lambda argv: argv\n"
            "configure()\n"
            "ops.run(['tar', '--version'])\n"
        ),
    ],
)
def test_helper_external_alias_rebind_clears_old_executable(
    tmp_path: Path,
    source: str,
) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, source)

    assert mandatory_executable_gaps(tmp_path, _declaration(relative)) == []


def test_replay_state_helpers_reject_invalid_merges_and_collect_lexical_binders() -> None:
    assert replay.merge_instance_owners(()) == {}
    with pytest.raises(replay.ReplayStateError):
        replay.BranchState.merge(())
    with pytest.raises(replay.ReplayStateError):
        replay.merge_callable_scopes(((), ({},)))
    with pytest.raises(replay.ReplayStateError):
        replay.merge_deferred_scopes(((), ((),)))

    arguments = ast.parse(
        "def invoke(positional, /, *values, keyword, **options):\n    pass\n"
    ).body[0]
    assert isinstance(arguments, ast.FunctionDef)
    assert replay.argument_names(arguments.args) == {
        "positional",
        "values",
        "keyword",
        "options",
    }

    scope = ast.parse(
        "def invoke():\n"
        "    from package import imported\n"
        "    try:\n"
        "        pass\n"
        "    except Exception as failure:\n"
        "        pass\n"
        "    match value:\n"
        "        case [*items]:\n"
        "            pass\n"
        "        case {'entry': captured, **remaining}:\n"
        "            pass\n"
        "    async def async_task():\n"
        "        pass\n"
        "    class Container:\n"
        "        pass\n"
    ).body[0]
    assert isinstance(scope, ast.FunctionDef)
    local_names, global_names, nonlocal_names = replay.function_scope_bindings(scope.body)
    assert {
        "imported",
        "failure",
        "items",
        "captured",
        "remaining",
        "async_task",
        "Container",
    }.issubset(local_names)
    assert global_names == frozenset()
    assert nonlocal_names == frozenset()

    anonymous_patterns = replay._FunctionLocalBinderCollector()  # noqa: RUF100, SLF001 - coverage exercises exact lexical-state guard
    anonymous_patterns.visit(ast.ImportFrom(module="package", names=[ast.alias(name="*")]))
    anonymous_patterns.visit(ast.MatchAs(pattern=None, name=None))
    anonymous_patterns.visit(ast.MatchStar(name=None))
    anonymous_patterns.visit(ast.MatchMapping(keys=[], patterns=[], rest=None))
    assert anonymous_patterns.names == set()


def test_replay_guards_recursive_and_repeated_inline_callables() -> None:
    tree = ast.parse(
        "def recurse():\n"
        "    recurse()\n"
        "recurse()\n"
        "class Container:\n"
        "    invoke = lambda: None\n"
        "(lambda: None)()\n"
    )
    collector = _ExecutionCallCollector()
    collector.visit(tree)

    inline_call = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Lambda)
    )
    collector._replay_inline_lambda(inline_call.func)  # noqa: RUF100, SLF001 - coverage exercises exact lexical-state guard

    assert collector.calls == []
    assert "Container.invoke" in collector._class_callables  # noqa: RUF100, SLF001 - coverage exercises exact lexical-state guard
