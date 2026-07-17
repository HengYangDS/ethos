from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

_GOOGLE_SECTIONS = {
    "Args",
    "Arguments",
    "Attributes",
    "Examples",
    "Note",
    "Notes",
    "Raises",
    "Returns",
    "Yields",
}
_LEGACY_FIELD_RE = re.compile(r"^\s*:(?:param|type|returns?|rtype|raises?)\b")


@dataclass(frozen=True, slots=True)
class DocstringStyleIssue:
    """A style or signature violation in an existing docstring."""

    path: str
    qualified_name: str
    line: int
    code: str
    message: str

    def to_dict(self) -> dict[str, object]:
        """Return the stable JSON form used by the docstring gate."""
        return {
            "path": self.path,
            "qualified_name": self.qualified_name,
            "line": self.line,
            "code": self.code,
            "message": self.message,
        }


def style_issues(
    root: Path,
    policy: dict[str, Any],
    *,
    python_files: Callable[[Path, dict[str, Any]], list[Path]],
    module_name: Callable[[str], str],
) -> list[DocstringStyleIssue]:
    if str(policy.get("style", "google")).lower() != "google":
        return []
    issues: list[DocstringStyleIssue] = []
    for path in python_files(root, policy):
        rel = path.relative_to(root).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        module = module_name(rel)
        module_docstring = ast.get_docstring(tree)
        if module_docstring:
            issues.extend(docstring_issues(rel, module or "<module>", 1, module_docstring))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            docstring = ast.get_docstring(node)
            if not docstring:
                continue
            qualified = f"{module}.{node.name}" if module else node.name
            issues.extend(docstring_issues(rel, qualified, node.lineno, docstring))
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and bool(
                policy.get("check_structured_signature", True)
            ):
                issues.extend(signature_issues(rel, qualified, node, docstring))
    return issues


def docstring_issues(
    rel: str,
    qualified_name: str,
    line: int,
    docstring: str,
) -> list[DocstringStyleIssue]:
    issues: list[DocstringStyleIssue] = []
    summary = docstring.strip().splitlines()[0].strip() if docstring.strip() else ""
    if not summary:
        issues.append(issue(rel, qualified_name, line, "empty", "docstring must have a summary"))
    elif summary.endswith(":"):
        issues.append(
            issue(rel, qualified_name, line, "summary_colon", "summary must be a sentence")
        )
    if weak_summary(summary):
        issues.append(issue(rel, qualified_name, line, "weak_summary", "summary is too generic"))
    issues.extend(
        issue(rel, qualified_name, line, "legacy_style", f"legacy docstring marker: {marker}")
        for marker in legacy_docstring_markers(docstring)
    )
    issues.extend(
        issue(
            rel,
            qualified_name,
            line,
            "unknown_section",
            f"non-Google section heading: {section}",
        )
        for section in section_names(docstring)
        if section not in _GOOGLE_SECTIONS
    )
    return issues


def signature_issues(
    rel: str,
    qualified_name: str,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    docstring: str,
) -> list[DocstringStyleIssue]:
    doc_sections = sections(docstring)
    if "Args" not in doc_sections and "Arguments" not in doc_sections:
        return []
    documented = documented_args(doc_sections.get("Args", ()) + doc_sections.get("Arguments", ()))
    signature_args = set(signature_arg_names(node))
    missing = sorted(signature_args - documented)
    extra = sorted(documented - signature_args)
    issues: list[DocstringStyleIssue] = []
    if missing:
        issues.append(
            issue(
                rel,
                qualified_name,
                node.lineno,
                "args_missing",
                "Args section missing: " + ", ".join(missing),
            )
        )
    if extra:
        issues.append(
            issue(
                rel,
                qualified_name,
                node.lineno,
                "args_extra",
                "Args section documents unknown names: " + ", ".join(extra),
            )
        )
    return issues


def signature_arg_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[str, ...]:
    args = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
    names = [arg.arg for arg in args if arg.arg not in {"self", "cls"}]
    if node.args.vararg is not None:
        names.append(node.args.vararg.arg)
    if node.args.kwarg is not None:
        names.append(node.args.kwarg.arg)
    return tuple(names)


def documented_args(lines: tuple[str, ...]) -> set[str]:
    names: set[str] = set()
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith(("-", "*")):
            stripped = stripped[1:].strip()
        match = re.match(r"([*]{0,2}[A-Za-z_][A-Za-z0-9_]*)\s*(?:\(|:|\s-)", stripped)
        if match:
            names.add(match.group(1).lstrip("*"))
    return names


def sections(docstring: str) -> dict[str, tuple[str, ...]]:
    found: dict[str, list[str]] = {}
    current: str | None = None
    for line in docstring.splitlines()[1:]:
        stripped = line.strip()
        if stripped.endswith(":") and stripped[:-1] in _GOOGLE_SECTIONS:
            current = stripped[:-1]
            found.setdefault(current, [])
            continue
        if current is not None:
            if stripped.endswith(":") and not line.startswith((" ", "\t")):
                current = None
            else:
                found[current].append(line)
    return {key: tuple(value) for key, value in found.items()}


def section_names(docstring: str) -> tuple[str, ...]:
    names = []
    for line in docstring.splitlines()[1:]:
        stripped = line.strip()
        if stripped.endswith(":") and re.match(r"^[A-Z][A-Za-z ]+$", stripped[:-1]):
            names.append(stripped[:-1])
    return tuple(names)


def legacy_docstring_markers(docstring: str) -> tuple[str, ...]:
    markers: list[str] = []
    lines = docstring.splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if _LEGACY_FIELD_RE.match(stripped):
            markers.append(stripped.split()[0])
        if index + 1 < len(lines) and set(lines[index + 1].strip()) == {"-"}:
            markers.append(stripped)
    return tuple(markers)


def weak_summary(summary: str) -> bool:
    normalized = summary.strip().rstrip(".").lower()
    return normalized in {"helper", "utility", "todo", "tbd"}


def issue(
    rel: str,
    qualified_name: str,
    line: int,
    code: str,
    message: str,
) -> DocstringStyleIssue:
    return DocstringStyleIssue(
        path=rel,
        qualified_name=qualified_name,
        line=line,
        code=code,
        message=message,
    )
