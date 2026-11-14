"""Two-way static checks that the gap registry and the sources agree."""

from __future__ import annotations

import ast
from operator import itemgetter
from pathlib import Path

import pytest

from ethos.contracts.codes import gaps

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src" / "ethos"
HELPERS = {"refuse": 0, "refusal": 0, "require": 1, "present": 1, "instance": 2}
RAISED = {"ValueError", "TypeError", "RuntimeError"}
PROSE_CEILING = 127
_STRINGS = (ast.Constant, ast.JoinedStr)


def _head(node: ast.expr) -> str:
    """The literal head of a literal or f-string, or the empty string."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr) and node.values:
        first = node.values[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            return first.value
    return ""


def _expressions(tree: ast.Module) -> list[tuple[int, ast.expr]]:
    """Every expression that reaches a refusal helper's gap argument or a raised error's first."""
    runs = sorted(
        (
            (target.id, node.lineno, node.value)
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign) and isinstance(node.value, _STRINGS)
            for target in node.targets
            if isinstance(target, ast.Name)
            and not (isinstance(node.value, ast.Constant) and not isinstance(node.value.value, str))
        ),
        key=itemgetter(1),
    )

    def resolve(node: ast.expr, line: int) -> ast.expr:
        """The value a name bound before the site holds; the plan's rule stops at one local."""
        if isinstance(node, ast.Name):
            earlier = [run for run in runs if run[0] == node.id and run[1] < line]
            return earlier[-1][2] if earlier else node
        return node

    found: list[tuple[int, ast.expr]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
            if name in HELPERS and len(node.args) > HELPERS[name]:
                found.extend(
                    (node.lineno, resolve(argument, node.lineno))
                    for argument in node.args[HELPERS[name] :]
                )
        elif isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call) and node.exc.args:
            label = getattr(node.exc.func, "id", getattr(node.exc.func, "attr", ""))
            if label in RAISED:
                found.append((node.lineno, resolve(node.exc.args[0], node.lineno)))
    return found


def _sources() -> list[Path]:
    return sorted(SOURCE.rglob("*.py"))


def test_every_site_that_raises_a_code_registers_it_or_speaks_prose() -> None:
    """Test (1): a literal or head at a refusal or raise position is a code or a family member."""
    unregistered: list[str] = []
    prose: set[str] = set()
    for path in _sources():
        for line, node in _expressions(ast.parse(path.read_text(encoding="utf-8"))):
            code = gaps.gap_code(_head(node))
            if not code or gaps.registered(code):
                continue
            if gaps.code_shaped(code):
                unregistered.append(f"{path.relative_to(ROOT).as_posix()}:{line}:{code}")
            else:
                prose.add(f"{path.relative_to(ROOT).as_posix()}:{line}")
    assert unregistered == []
    assert len(prose) <= PROSE_CEILING, sorted(prose)


def test_every_registered_code_occurs_or_is_declared_reserved() -> None:
    """Test (2): a row names a code some source literal carries, or it is reserved on purpose."""
    text = "\n".join(path.read_text(encoding="utf-8") for path in _sources())
    absent = [
        code for code, row in gaps.records().items() if code not in text and not row.get("reserved")
    ]
    assert absent == [], absent[:20]


def test_every_row_names_a_package_owner_and_the_rows_are_sorted() -> None:
    """Test (3): each owner is an importable package, and the table reads in code order."""
    codes = list(gaps.records())
    assert codes == sorted(codes)
    for code, row in gaps.records().items():
        owner = row["owner"]
        assert owner == "ethos" or (SOURCE.joinpath(*owner.split(".")) / "__init__.py").exists()
        assert code == code.lower()
        assert ":" not in code


@pytest.mark.parametrize(
    ("gap", "known", "repair"),
    [
        ("repository_paradigm_docs:AGENTS.md", True, ""),
        ("no_such_family_member", False, ""),
        ("candidate_base_stale:x", True, "ethos lane refresh-base"),
    ],
)
def test_the_loader_registers_families_and_reports_the_unknown(
    gap: str, repair: str, *, known: bool
) -> None:
    assert gaps.registered(gaps.gap_code(gap)) is known
    assert gaps.repair_for(gap).startswith(repair)


@pytest.mark.parametrize(
    ("gap", "code"),
    [
        ("repository_invalid", "repository_invalid"),
        ("host_declaration_invalid:slots", "host_declaration_invalid"),
        ("", ""),
    ],
)
def test_a_gaps_code_is_the_text_before_its_first_colon(gap: str, code: str) -> None:
    assert gaps.gap_code(gap) == code
