"""Product code builds every declared name and carrier path from the paradigm declaration."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from ethos.contracts.paradigm.declaration import load_repository_paradigm

ROOT = Path(__file__).resolve().parents[2]
OWNER = "src/ethos/contracts/paradigm/"
# Delivery acceptance runs outside a governed repository's proof; its owners migrate these values,
# so the count only falls.
TOOLS_RESTATEMENTS = 17


def test_product_code_restates_no_declared_value_and_tools_only_shed_theirs() -> None:
    """`src/` builds every declared value from the paradigm; `tools/` keeps at most its count."""
    assert _restatements(ROOT, "src") == []
    assert len(_restatements(ROOT, "tools")) <= TOOLS_RESTATEMENTS


@pytest.mark.parametrize(
    ("source", "found"),
    [
        ('path = ".ethos/release.toml"', 1),
        ('gap = "repository_profile_invalid:.ethos/profile.toml"', 1),
        ('rules = root / "rules.toml"', 1),
        ('carrier = f"{root}/workspace.toml"', 1),
        ('branch = "candidate/dev"\nchangelog = "CHANGELOG.md"', 2),
        ('gap = "product_version_missing:VERSION"\nshow = f"{commit}:VERSION"', 2),
        ('"""Read `.ethos/rules.toml`."""\ngroup = "dev"\nbranch = "main"', 0),
    ],
)
def test_a_restated_value_is_found_and_a_docstring_or_single_word_is_not(
    tmp_path: Path, source: str, found: int
) -> None:
    """A planted restatement fails the check; prose and single-word names stay allowed."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src/planted.py").write_text(source, encoding="utf-8")
    assert len(_restatements(tmp_path, "src")) == found


def _restatements(root: Path, prefix: str) -> list[str]:
    """List each non-docstring string constant under a root that restates a declared value."""
    paradigm = load_repository_paradigm()
    names = tuple(paradigm.binding.files.values())
    carriers = (paradigm.release.version_file, paradigm.release.changelog)
    branch = paradigm.branch
    branches = (branch.candidate, branch.work_prefix, branch.proposal_prefix)
    equal = {*names, *carriers, *branches}
    contained = (
        *(f"/{name}" for name in names),
        *(f"{mark}{name}" for name in carriers for mark in ":/"),
    )
    found = []
    for path in sorted((root / prefix).rglob("*.py")):
        relative = path.relative_to(root).as_posix()
        if relative.startswith(OWNER):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        documented = {id(node) for node in _docstrings(tree)}
        found += [
            f"{relative}:{node.lineno}:{node.value}"
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in documented
            and (node.value in equal or any(value in node.value for value in contained))
        ]
    return found


def _docstrings(tree: ast.Module) -> list[ast.Constant]:
    """Return the docstring constants of a module and of its classes and functions."""
    owners = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
    ]
    return [
        owner.body[0].value
        for owner in owners
        if owner.body
        and isinstance(owner.body[0], ast.Expr)
        and isinstance(owner.body[0].value, ast.Constant)
    ]
