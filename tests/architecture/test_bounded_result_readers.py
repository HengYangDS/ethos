"""Every ETHOS reader of another ETHOS process's JSON result expands a bounded result first."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
# Modules whose `--root` and `--json` argvs run other tools: gh and glab rows, and OpenSpec output.
_FOREIGN_ARGVS = frozenset(
    {
        "src/ethos/adapters/mutation/publication/retirement.py",
        "tools/ci/delivery/acceptance/first_change.py",
    }
)
# Modules that read the ETHOS-shaped report of their own helper program, which no bound shortens.
_FOREIGN_REPORTS = frozenset({"src/ethos/adapters/openspec/configuration.py"})
_ETHOS_FIELDS = frozenset({"required_gaps", "missing_facts_or_evidence", "bound"})
_PARSES = frozenset({"loads", "model_validate_json"})
_ARGV = 'argv = ("python", "-m", "ethos.cli")\n'
_HELPER = "def full(p):\n    return expand_result(p)\n"


def test_readers_of_ethos_results_expand_them() -> None:
    """`Readers of another ETHOS process read its result in full` holds in src/ and tools/."""
    assert [found for tree in ("src", "tools") for found in _unexpanded(ROOT, ROOT / tree)] == []


def test_the_installed_mcp_acceptance_needs_no_repository_tools() -> None:
    """The installed-package smoke runs this script under `python -I`, where `tools` is absent."""
    script = ast.parse((ROOT / "tools/ci/delivery/acceptance/mcp.py").read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(script):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert sorted(name for name in imported if name.split(".")[0] == "tools") == []


@pytest.mark.parametrize(
    ("source", "found"),
    [
        (_ARGV + "def f(run):\n    return json.loads(run.stdout)", 1),
        (_ARGV + "def f(run):\n    return expand_result(json.loads(run.stdout))", 0),
        (_ARGV + "def f(run):\n    p = json.loads(run.stdout)\n    return expand_result(p)", 0),
        (_ARGV + _HELPER + "def f(stdout):\n    return full(json.loads(stdout))", 0),
        (_ARGV + "def f(run):\n    return Model.model_validate_json(run.stdout)", 1),
        (_ARGV + "def f(path):\n    return json.loads(path.read_text())", 0),
        ('argv = ("gh", "--root", "--json")\ndef f(run):\n    return json.loads(run.stdout)', 1),
        ("def f(run):\n    return json.loads(run.stdout)['rows']", 0),
        ("def f(raw):\n    return json.loads(raw)['required_gaps']", 1),
        ("def f(raw):\n    p = json.loads(raw)\n    return 'command' in p and p.get('bound')", 1),
    ],
)
def test_a_reader_is_found_by_its_argv_or_by_the_fields_it_reads(
    tmp_path: Path, source: str, found: int
) -> None:
    """A planted reader that skips the bound fails the check; any other parse stays allowed."""
    (tmp_path / "planted.py").write_text(source, encoding="utf-8")
    assert len(_unexpanded(tmp_path, tmp_path)) == found


def _unexpanded(base: Path, tree: Path) -> list[str]:
    """List each parse of an ETHOS result that no expander receives, as `path:line`."""
    found: dict[str, None] = {}
    for path in sorted(tree.rglob("*.py")):
        module = ast.parse(path.read_text(encoding="utf-8"))
        relative = path.relative_to(base).as_posix()
        argv = relative not in _FOREIGN_ARGVS and _runs_ethos(module)
        fields = relative not in _FOREIGN_REPORTS
        expanders = _expanders(module)
        for function in ast.walk(module):
            if isinstance(function, ast.FunctionDef | ast.AsyncFunctionDef):
                for parse in _readers(function, argv=argv, fields=fields, expanders=expanders):
                    found[f"{relative}:{parse.lineno}"] = None
    return list(found)


def _name(call: ast.Call) -> str:
    func = call.func
    return func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")


def _runs_ethos(module: ast.Module) -> bool:
    """An argv that holds `ethos.cli`, or both of ETHOS's `--root` and `--json` flags."""
    for node in ast.walk(module):
        if isinstance(node, ast.Tuple | ast.List):
            items = {item.value for item in node.elts if isinstance(item, ast.Constant)}
            if "ethos.cli" in items or {"--root", "--json"} <= items:
                return True
    return False


def _expanders(module: ast.Module) -> frozenset[str]:
    """`expand_result` and each module-level function that passes it one of its parameters."""
    names = {"expand_result"}
    for node in module.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            parameters = {
                argument.arg for argument in ast.walk(node.args) if isinstance(argument, ast.arg)
            }
            calls = (call for call in ast.walk(node) if isinstance(call, ast.Call))
            if any(
                _name(call) == "expand_result"
                and any(isinstance(arg, ast.Name) and arg.id in parameters for arg in call.args)
                for call in calls
            ):
                names.add(node.name)
    return frozenset(names)


def _readers(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    argv: bool,
    fields: bool,
    expanders: frozenset[str],
) -> list[ast.Call]:
    """Each parse in one function that must expand an ETHOS result and does not."""
    nodes = list(ast.walk(function))
    parents = {id(child): node for node in nodes for child in ast.iter_child_nodes(node)}
    expanded = [
        arg
        for call in nodes
        if isinstance(call, ast.Call) and _name(call) in expanders
        for arg in call.args
    ]
    expanded_names = {arg.id for arg in expanded if isinstance(arg, ast.Name)}
    assigned = {
        id(node.value): node.targets[0].id
        for node in nodes
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
    }
    shaped = {name for node in nodes for name in _ethos_shaped(node)}
    return [
        parse
        for parse in nodes
        if isinstance(parse, ast.Call)
        and _name(parse) in _PARSES
        and (
            (argv and _of_stdout(parse))
            or (fields and assigned.get(id(parse)) in shaped)
            or (fields and _read_directly(parse, parents))
        )
        and not any(parse is arg for arg in expanded)
        and assigned.get(id(parse)) not in expanded_names
    ]


def _of_stdout(parse: ast.Call) -> bool:
    """A parse of a process's stdout: an attribute `.stdout` or a name `stdout`."""
    return any(
        (isinstance(node, ast.Attribute) and node.attr == "stdout")
        or (isinstance(node, ast.Name) and node.id == "stdout")
        for argument in parse.args
        for node in ast.walk(argument)
    )


def _ethos_shaped(node: ast.AST) -> tuple[str, ...]:
    """The names an expression reads for ETHOS's own fields or tests for its `command` key."""
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
        key = node.slice
        return (
            (node.value.id,) if isinstance(key, ast.Constant) and key.value in _ETHOS_FIELDS else ()
        )
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get"
    ):
        owner, key = node.func.value, node.args[0] if node.args else None
        fields = isinstance(key, ast.Constant) and key.value in _ETHOS_FIELDS
        return (owner.id,) if fields and isinstance(owner, ast.Name) else ()
    if (
        isinstance(node, ast.Compare)
        and isinstance(node.left, ast.Constant)
        and node.left.value == "command"
    ):
        return tuple(item.id for item in node.comparators if isinstance(item, ast.Name))
    return ()


def _read_directly(parse: ast.Call, parents: dict[int, ast.AST]) -> bool:
    """A parse whose own result is subscripted for an ETHOS field, as `json.loads(x)['bound']`."""
    parent = parents.get(id(parse))
    return (
        isinstance(parent, ast.Subscript)
        and isinstance(parent.slice, ast.Constant)
        and parent.slice.value in _ETHOS_FIELDS
    )
