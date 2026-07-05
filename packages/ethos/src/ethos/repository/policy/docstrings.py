"""Public-surface docstring coverage policy."""

from __future__ import annotations

import ast
import fnmatch
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_POLICY_PATH = Path(".config/checks/docstrings/policy.toml")
_DEFAULT_PATHS = ("packages/ethos/src", "packages/ethos-core/src")
_DEFAULT_FAIL_UNDER = 95.0


@dataclass(frozen=True)
class PublicSurfaceSymbol:
    """A Python symbol whose docstring forms part of the public product surface."""

    path: str
    qualified_name: str
    kind: str
    line: int
    documented: bool

    def to_dict(self) -> dict[str, object]:
        """Return the stable JSON form used by `ethos quality docstrings`."""
        return {
            "path": self.path,
            "qualified_name": self.qualified_name,
            "kind": self.kind,
            "line": self.line,
            "documented": self.documented,
        }


def docstring_coverage_report(root: Path) -> dict[str, object]:
    """Report public-surface docstring coverage for a repository."""
    policy = _load_policy(root)
    symbols = _public_symbols(root, policy)
    public_count = len(symbols)
    documented_count = sum(1 for symbol in symbols if symbol.documented)
    coverage = 100.0 if public_count == 0 else documented_count * 100.0 / public_count
    fail_under = float(policy.get("fail_under", _DEFAULT_FAIL_UNDER))
    missing = [symbol.to_dict() for symbol in symbols if not symbol.documented]
    gaps = []
    if coverage < fail_under:
        gaps.append(f"docstring_coverage_below_minimum:{coverage:.2f}<{fail_under:.2f}")
    if missing:
        gaps.extend(
            f"public_docstring_missing:{item['path']}:{item['qualified_name']}"
            for item in missing[:20]
        )
    return {
        "ok": not gaps,
        "state": "clean" if not gaps else "blocked",
        "policy": _POLICY_PATH.as_posix(),
        "paths": list(_paths(policy)),
        "fail_under": fail_under,
        "coverage_percent": round(coverage, 2),
        "documented_count": documented_count,
        "public_count": public_count,
        "missing": missing,
        "required_gaps": gaps,
    }


def _load_policy(root: Path) -> dict[str, Any]:
    path = root / _POLICY_PATH
    if not path.exists():
        return {"paths": list(_DEFAULT_PATHS), "fail_under": _DEFAULT_FAIL_UNDER}
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _paths(policy: dict[str, Any]) -> tuple[str, ...]:
    paths = policy.get("paths", _DEFAULT_PATHS)
    return tuple(str(path) for path in paths)


def _public_symbols(root: Path, policy: dict[str, Any]) -> list[PublicSurfaceSymbol]:
    symbols: list[PublicSurfaceSymbol] = []
    for configured in _paths(policy):
        base = root / configured
        if base.is_file() and base.suffix == ".py":
            candidates = [base]
        elif base.exists():
            candidates = sorted(base.rglob("*.py"))
        else:
            candidates = []
        for path in candidates:
            rel = path.relative_to(root).as_posix()
            if _excluded(rel, policy):
                continue
            symbols.extend(_file_symbols(root, path))
    return symbols


def _excluded(rel: str, policy: dict[str, Any]) -> bool:
    for root in policy.get("exclude_roots", ()):  # policy term, not filesystem root
        token = str(root).strip("/")
        if rel == token or rel.startswith(f"{token}/") or f"/{token}/" in rel:
            return True
    return False


def _file_symbols(root: Path, path: Path) -> list[PublicSurfaceSymbol]:
    rel = path.relative_to(root).as_posix()
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
    module_name = _module_name(rel)
    symbols: list[PublicSurfaceSymbol] = []
    if path.name == "__init__.py":
        symbols.append(
            PublicSurfaceSymbol(
                path=rel,
                qualified_name=module_name,
                kind="package_boundary",
                line=1,
                documented=bool(ast.get_docstring(tree)),
            )
        )
    exports = _explicit_exports(tree)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            if _is_cli_command(node) or node.name in exports:
                symbols.append(_symbol(rel, module_name, node, "function"))
        elif isinstance(node, ast.ClassDef) and node.name in exports:
            symbols.append(_symbol(rel, module_name, node, "class"))
    return symbols


def _symbol(
    rel: str,
    module_name: str,
    node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
    kind: str,
) -> PublicSurfaceSymbol:
    return PublicSurfaceSymbol(
        path=rel,
        qualified_name=f"{module_name}.{node.name}",
        kind=kind,
        line=node.lineno,
        documented=bool(ast.get_docstring(node)),
    )


def _module_name(rel: str) -> str:
    path = rel.removesuffix(".py")
    parts = path.split("/")
    if "src" in parts:
        parts = parts[parts.index("src") + 1 :]
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _explicit_exports(tree: ast.Module) -> set[str]:
    exports: set[str] = set()
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        targets_all = (
            isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets
        )
        if not any(targets_all):
            continue
        if isinstance(node.value, ast.List | ast.Tuple | ast.Set):
            for item in node.value.elts:
                if isinstance(item, ast.Constant) and isinstance(item.value, str):
                    exports.add(item.value)
    return exports


def _is_cli_command(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return any(_decorator_is_command(decorator) for decorator in node.decorator_list)


def _decorator_is_command(decorator: ast.expr) -> bool:
    if isinstance(decorator, ast.Call):
        return _decorator_is_command(decorator.func)
    if isinstance(decorator, ast.Attribute):
        return decorator.attr == "command"
    if isinstance(decorator, ast.Name):
        return fnmatch.fnmatch(decorator.id, "*command")
    return False
