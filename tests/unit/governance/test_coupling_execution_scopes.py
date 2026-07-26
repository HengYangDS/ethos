from __future__ import annotations

import ast
from typing import TYPE_CHECKING

import pytest

from ethos.repository.policy.coupling.execution.audit import mandatory_executable_gaps
from ethos.repository.policy.coupling.execution.collector import _ExecutionCallCollector
from ethos.repository.policy.coupling.execution.collector import _instance_constructor_owner
from ethos.repository.policy.coupling.execution.collector import collect_external_execution_calls
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


def _gaps(root: Path, relative: str) -> list[str]:
    return mandatory_executable_gaps(root, _declaration(relative))


def _write(root: Path, relative: str, source: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


@pytest.mark.parametrize(
    ("source", "line"),
    [
        (
            "class Runner:\n"
            "    def execute(self):\n"
            "        process.run(['tar', '--version'])\n"
            "import subprocess as process\n",
            3,
        ),
        (
            "class Runner:\n"
            "    async def execute(self):\n"
            "        process.run(['tar', '--version'])\n"
            "import subprocess as process\n",
            3,
        ),
        (
            "execute = lambda: process.run(['tar', '--version'])\nimport subprocess as process\n",
            1,
        ),
        (
            "def outer():\n"
            "    def execute():\n"
            "        process.run(['tar', '--version'])\n"
            "    import subprocess as process\n"
            "    execute()\n",
            3,
        ),
    ],
)
def test_deferred_callable_scopes_use_late_enclosing_aliases(
    tmp_path: Path,
    source: str,
    line: int,
) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, source)

    assert _gaps(tmp_path, relative) == [
        f"mandatory_executable_undeclared:{_BINDING_ID}:{relative}:{line}:tar"
    ]


def test_match_case_guard_execution_is_audited(tmp_path: Path) -> None:
    relative = "mandatory/effect.py"
    _write(
        tmp_path,
        relative,
        "import subprocess\n"
        "match value:\n"
        "    case _ if subprocess.run(['tar', '--version']):\n"
        "        pass\n",
    )

    assert _gaps(tmp_path, relative) == [
        f"mandatory_executable_undeclared:{_BINDING_ID}:{relative}:3:tar"
    ]


@pytest.mark.parametrize(
    "source",
    [
        "import subprocess as process\n"
        "def execute():\n"
        "    process.run(['tar', '--version'])\n"
        "    process = object()\n"
        "execute()\n",
        "import subprocess as process\n"
        "with object() as process:\n"
        "    process.run(['tar', '--version'])\n",
        "import subprocess as process\n"
        "[process.run(['tar', '--version']) for process in (object(),)]\n",
        "import subprocess as process\n"
        "match object():\n"
        "    case process:\n"
        "        process.run(['tar', '--version'])\n",
        "import subprocess\n"
        "def execute(run=subprocess.run):\n"
        "    run = lambda arguments: arguments\n"
        "    run(['tar', '--version'])\n"
        "execute()\n",
    ],
)
def test_local_binding_forms_shadow_execution_aliases(tmp_path: Path, source: str) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, source)

    assert _gaps(tmp_path, relative) == []


@pytest.mark.parametrize(
    ("source", "line"),
    [
        (
            "import subprocess\n"
            "def execute(run=subprocess.run):\n"
            "    run(['tar', '--version'])\n"
            "execute()\n",
            3,
        ),
        (
            "import subprocess\n"
            "def execute(run=subprocess.run):\n"
            "    run(['tar', '--version'])\n"
            "    run = lambda arguments: arguments\n"
            "execute()\n",
            3,
        ),
        (
            "import subprocess\n"
            "def execute(run=subprocess.run):\n"
            "    run(['tar', '--version'])\n"
            "    del run\n"
            "execute()\n",
            3,
        ),
        (
            "import subprocess\n"
            "for process in (subprocess,):\n"
            "    process.run(['tar', '--version'])\n",
            3,
        ),
        (
            "import subprocess\n[invoke(['tar', '--version']) for invoke in (subprocess.run,)]\n",
            2,
        ),
        (
            "import subprocess\n"
            "match subprocess:\n"
            "    case process:\n"
            "        process.run(['tar', '--version'])\n",
            4,
        ),
        (
            "import subprocess\n"
            "match {'run': subprocess.run}:\n"
            "    case {'run': invoke}:\n"
            "        invoke(['tar', '--version'])\n",
            4,
        ),
        (
            "import subprocess\n"
            "def execute():\n"
            "    global subprocess\n"
            "    subprocess.run(['tar', '--version'])\n"
            "execute()\n",
            4,
        ),
        (
            "def outer():\n"
            "    import subprocess as process\n"
            "    def execute():\n"
            "        nonlocal process\n"
            "        process.run(['tar', '--version'])\n"
            "    execute()\n"
            "outer()\n",
            5,
        ),
        (
            "import subprocess\n"
            "[invoke(['tar', '--version']) for value in (subprocess.run,) if (invoke := value)]\n",
            2,
        ),
    ],
)
def test_static_bindings_in_defaults_iteration_and_match_are_audited(
    tmp_path: Path,
    source: str,
    line: int,
) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, source)

    assert _gaps(tmp_path, relative) == [
        f"mandatory_executable_undeclared:{_BINDING_ID}:{relative}:{line}:tar"
    ]


@pytest.mark.parametrize(
    "source",
    [
        "import subprocess as process\n"
        "invoke = lambda: process.run(['tar', '--version'])\n"
        "invoke()\n"
        "process = object()\n",
        "import subprocess as process\n"
        "invoke = lambda: process.run(['tar', '--version'])\n"
        "call = invoke\n"
        "call()\n"
        "process = object()\n",
        "import subprocess as process\n"
        "(lambda: process.run(['tar', '--version']))()\n"
        "process = object()\n",
    ],
)
def test_lambda_calls_use_their_early_call_site_alias_state(tmp_path: Path, source: str) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, source)

    assert _gaps(tmp_path, relative) == [
        f"mandatory_executable_undeclared:{_BINDING_ID}:{relative}:2:tar"
    ]


def test_lexical_edge_forms_preserve_alias_boundaries() -> None:
    tree = ast.parse(
        "import subprocess\n"
        "from . import local_only\n"
        "class Meta(metaclass=type):\n"
        "    pass\n"
        "try:\n"
        "    pass\n"
        "except:\n"
        "    pass\n"
        "try:\n"
        "    pass\n"
        "except* Exception:\n"
        "    pass\n"
        "del (before, (after, final))\n"
        "async def execute(*items, **options):\n"
        "    async for (left, right) in ((),):\n"
        "        pass\n"
        "    async with manager() as (resource,):\n"
        "        pass\n"
        "    match {'run': subprocess.run}:\n"
        "        case {'run': (object() as invoke), **rest}:\n"
        "            invoke(['tar', '--version'])\n"
        "    match [subprocess.run]:\n"
        "        case [*operations]:\n"
        "            pass\n"
        "execute()\n"
    )

    calls = collect_external_execution_calls(tree)

    assert [function for _node, function in calls] == ["subprocess.run"]
    assert (
        _instance_constructor_owner(
            ast.parse("Unknown()").body[0].value,
            {},
            {},
        )
        is None
    )
    assert (
        _instance_constructor_owner(
            ast.parse("Known()").body[0].value,
            {"Known.run": frozenset({"subprocess.run"})},
            {},
        )
        == "Known"
    )

    collector = _ExecutionCallCollector()
    scope = collector._enter_scope(None)  # noqa: RUF100, SLF001 - coverage exercises exact lexical-state guard
    try:
        collector._global_function_aliases["shadowed"] = frozenset({"subprocess.run"})  # noqa: RUF100, SLF001 - coverage exercises exact lexical-state guard
        collector._scope_local_names[-1] = frozenset({"shadowed"})  # noqa: RUF100, SLF001 - coverage exercises exact lexical-state guard
        assert "shadowed" not in collector._resolution_aliases()[1]  # noqa: RUF100, SLF001 - coverage exercises exact lexical-state guard

        collector._set_current_alias_binding(  # noqa: RUF100, SLF001 - coverage exercises exact lexical-state guard
            "current",
            ({}, {"current": frozenset({"subprocess.run"})}, {}),
        )
        assert collector.function_aliases["current"] == frozenset({"subprocess.run"})
        collector._global_function_aliases["current"] = frozenset({"subprocess.run"})  # noqa: RUF100, SLF001 - coverage exercises exact lexical-state guard
        collector._erase("current")  # noqa: RUF100, SLF001 - coverage exercises exact lexical-state guard
        assert collector._global_function_aliases["current"] == frozenset({"subprocess.run"})  # noqa: RUF100, SLF001 - coverage exercises exact lexical-state guard

        collector._set_global_alias_binding(  # noqa: RUF100, SLF001 - coverage exercises exact lexical-state guard
            "global",
            frozenset(),
            frozenset({"subprocess.run"}),
        )
        assert collector._global_function_aliases["global"] == frozenset({"subprocess.run"})  # noqa: RUF100, SLF001 - coverage exercises exact lexical-state guard
        assert "global" not in collector.function_aliases

        collector._bind_pattern_value(  # noqa: RUF100, SLF001 - coverage exercises exact lexical-state guard
            ast.MatchAs(pattern=ast.MatchStar(name="captured"), name="alias"),
            ast.Name(id="value", ctx=ast.Load()),
        )
        collector._bind_pattern_value(  # noqa: RUF100, SLF001 - coverage exercises exact lexical-state guard
            ast.MatchMapping(
                keys=[ast.Name(id="dynamic", ctx=ast.Load())],
                patterns=[ast.MatchAs(pattern=None, name="unbound")],
                rest=None,
            ),
            ast.Dict(keys=[], values=[]),
        )
        collector._delete_target_aliases(  # noqa: RUF100, SLF001 - coverage exercises exact lexical-state guard
            ast.Starred(
                value=ast.Name(id="unsupported", ctx=ast.Del()),
                ctx=ast.Del(),
            )
        )
        assert "unbound" not in collector.function_aliases
        assert collector._merged_snapshot((collector._snapshot(), collector._snapshot())) == (  # noqa: RUF100, SLF001 - coverage exercises exact lexical-state guard
            collector._snapshot()  # noqa: RUF100, SLF001 - coverage exercises exact lexical-state guard
        )
    finally:
        collector._leave_scope(scope)  # noqa: RUF100, SLF001 - coverage exercises exact lexical-state guard
