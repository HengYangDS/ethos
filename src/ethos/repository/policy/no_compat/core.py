from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

PRODUCTION_SOURCE_ROOTS = (Path("src/ethos"),)
FORBIDDEN_PATH_PARTS = {
    "compat",
    "compatibility",
    "deprecated",
    "legacy",
    "shim",
    "wrapper",
    "wrappers",
}
FORBIDDEN_IDENTIFIER_PATTERNS = (
    ("compatibility_shim", re.compile(r"compat.*shim|shim.*compat", re.IGNORECASE)),
    ("compatibility_alias", re.compile(r"compat.*alias|alias.*compat", re.IGNORECASE)),
    ("compatibility_wrapper", re.compile(r"compat.*wrapp|wrapp.*compat", re.IGNORECASE)),
    ("compatibility_mode", re.compile(r"compat.*mode|mode.*compat", re.IGNORECASE)),
    ("legacy_shim", re.compile(r"legacy.*shim|shim.*legacy", re.IGNORECASE)),
    ("legacy_alias", re.compile(r"legacy.*alias|alias.*legacy", re.IGNORECASE)),
    ("legacy_wrapper", re.compile(r"legacy.*wrapp|wrapp.*legacy", re.IGNORECASE)),
    ("deprecated_alias", re.compile(r"deprecated.*alias|alias.*deprecated", re.IGNORECASE)),
    ("deprecated_wrapper", re.compile(r"deprecated.*wrapp|wrapp.*deprecated", re.IGNORECASE)),
)


@dataclass(frozen=True, slots=True)
class NoCompatFinding:
    """A compatibility-residue finding in production source."""

    path: str
    line: int
    kind: str
    detail: str

    @property
    def gap(self) -> str:
        """Return the required-gap string for this finding."""
        return f"no_compat_residue:{self.kind}:{self.path}:{self.line}:{self.detail}"

    def to_dict(self) -> dict[str, object]:
        """Serialize the finding for command JSON."""
        return {
            "path": self.path,
            "line": self.line,
            "kind": self.kind,
            "detail": self.detail,
            "gap": self.gap,
        }


def no_compat_report(root: Path) -> dict[str, object]:
    """Report production compatibility residue without scanning test fixtures."""
    findings: list[NoCompatFinding] = []
    scanned_paths: list[str] = []
    for source_root in PRODUCTION_SOURCE_ROOTS:
        base = root / source_root
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.py")):
            rel = path.relative_to(root).as_posix()
            scanned_paths.append(rel)
            findings.extend(_path_part_findings(root, path))
            findings.extend(_python_findings(root, path))
    required_gaps = [finding.gap for finding in findings]
    return {
        "ok": not findings,
        "state": "clean" if not findings else "blocked",
        "summary": {
            "finding_count": len(findings),
            "scanned_path_count": len(scanned_paths),
            "source_roots": [source.as_posix() for source in PRODUCTION_SOURCE_ROOTS],
        },
        "required_gaps": required_gaps,
        "findings": [finding.to_dict() for finding in findings],
    }


def _path_part_findings(root: Path, path: Path) -> list[NoCompatFinding]:
    rel = path.relative_to(root).as_posix()
    return [
        NoCompatFinding(rel, 1, "forbidden_path_part", part)
        for part in Path(rel).with_suffix("").parts
        if part.lower() in FORBIDDEN_PATH_PARTS
    ]


def _python_findings(root: Path, path: Path) -> list[NoCompatFinding]:
    rel = path.relative_to(root).as_posix()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        return [NoCompatFinding(rel, exc.lineno or 1, "syntax", "unparseable_python")]
    findings: list[NoCompatFinding] = []
    for node in ast.walk(tree):
        findings.extend(_definition_name_findings(rel, node))
        findings.extend(_import_name_findings(rel, node))
    return findings


def _definition_name_findings(rel: str, node: ast.AST) -> list[NoCompatFinding]:
    name = ""
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        name = node.name
    elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
        name = node.id
    return _identifier_findings(rel, getattr(node, "lineno", 1), name)


def _import_name_findings(rel: str, node: ast.AST) -> list[NoCompatFinding]:
    names: list[tuple[str, int]] = []
    if isinstance(node, ast.Import):
        names.extend((alias.name, node.lineno) for alias in node.names)
        names.extend((alias.asname or "", node.lineno) for alias in node.names)
    elif isinstance(node, ast.ImportFrom):
        names.append((node.module or "", node.lineno))
        names.extend((alias.name, node.lineno) for alias in node.names)
        names.extend((alias.asname or "", node.lineno) for alias in node.names)
    findings: list[NoCompatFinding] = []
    for name, line in names:
        findings.extend(_identifier_findings(rel, line, name, kind="forbidden_import"))
    return findings


def _identifier_findings(
    rel: str, line: int, name: str, *, kind: str = "forbidden_identifier"
) -> list[NoCompatFinding]:
    return [
        NoCompatFinding(rel, line, kind, detail)
        for detail, pattern in FORBIDDEN_IDENTIFIER_PATTERNS
        if name and pattern.search(name)
    ]
