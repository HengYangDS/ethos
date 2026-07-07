from __future__ import annotations

import ast
import tomllib
from collections import defaultdict
from pathlib import Path
from typing import Any

_POLICY_PATH = Path(".config/checks/module-layout/policy.toml")
_DEFAULT_PATHS = ("packages/ethos/src", "packages/ethos-core/src")
_DEFAULT_FLAT_DIRECTORY_LIMIT = 8
_DEFAULT_SUFFIX_GROUP_MIN = 3


def module_layout_report(root: Path) -> dict[str, object]:
    """Report module-layout violations enforced from `rules/module_layout.md`."""
    policy = _load_policy(root)
    suffix_modules = _suffix_module_findings(root, policy)
    suffix_groups = _suffix_group_findings(root, policy)
    flat_directories = _flat_directory_findings(root, policy)
    private_aliases = _private_alias_findings(root, policy)
    package_init_facades = _package_init_facade_findings(root, policy)
    baseline = _baseline(policy)
    findings = [
        *suffix_modules,
        *suffix_groups,
        *flat_directories,
        *private_aliases,
        *package_init_facades,
    ]
    current_gaps = {str(item["gap"]) for item in findings}
    stale_baselines = _stale_baseline_findings(baseline, current_gaps)
    baseline_limit = _baseline_limit(policy)
    baseline_limit_gaps = _baseline_limit_gaps(len(baseline), baseline_limit)
    gaps = [str(item["gap"]) for item in findings if item["gap"] not in baseline]
    gaps.extend(str(item["gap"]) for item in stale_baselines)
    gaps.extend(baseline_limit_gaps)
    return {
        "ok": not gaps,
        "state": "clean" if not gaps else "blocked",
        "policy": _POLICY_PATH.as_posix(),
        "flat_directory_limit": int(
            policy.get("flat_directory_limit", _DEFAULT_FLAT_DIRECTORY_LIMIT)
        ),
        "suffix_flat_group_min": int(
            policy.get("suffix_flat_group_min", _DEFAULT_SUFFIX_GROUP_MIN)
        ),
        "summary": {
            "suffix_module_count": len(suffix_modules),
            "suffix_flat_count": len(suffix_groups),
            "flat_directory_count": len(flat_directories),
            "private_alias_count": len(private_aliases),
            "package_init_facade_count": len(package_init_facades),
        },
        "suffix_module_findings": suffix_modules,
        "suffix_flat_findings": suffix_groups,
        "flat_directory_findings": flat_directories,
        "private_alias_findings": private_aliases,
        "package_init_facade_findings": package_init_facades,
        "stale_baseline_findings": stale_baselines,
        "baseline_gap_count": len(baseline),
        "baseline_limit": baseline_limit,
        "required_gaps": gaps,
    }


def _stale_baseline_findings(
    baseline: set[str],
    current_gaps: set[str],
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for gap in sorted(baseline - current_gaps):
        findings.append({"gap": f"module_layout_stale_baseline:{gap}", "baseline_gap": gap})
    return findings


def _baseline_limit(policy: dict[str, Any]) -> int | None:
    value = policy.get("baseline_gap_limit")
    if isinstance(value, int):
        return value
    return None


def _baseline_limit_gaps(count: int, limit: int | None) -> list[str]:
    if count == 0:
        return []
    if limit is None:
        return ["module_layout_baseline_limit_missing"]
    if count == limit:
        return []
    if count > limit:
        return [f"module_layout_baseline_limit:{count}>{limit}"]
    return [f"module_layout_baseline_limit:{count}!={limit}"]


def _load_policy(root: Path) -> dict[str, Any]:
    path = root / _POLICY_PATH
    if not path.exists():
        return {
            "paths": list(_DEFAULT_PATHS),
            "flat_directory_limit": _DEFAULT_FLAT_DIRECTORY_LIMIT,
            "suffix_flat_group_min": _DEFAULT_SUFFIX_GROUP_MIN,
        }
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _baseline(policy: dict[str, Any]) -> set[str]:
    return {
        *set(_string_list(policy.get("allowed_suffix_modules"))),
        *set(_string_list(policy.get("allowed_suffix_flat"))),
        *set(_string_list(policy.get("allowed_flat_directories"))),
        *set(_string_list(policy.get("allowed_private_aliases"))),
        *set(_string_list(policy.get("allowed_package_init_facades"))),
    }


def _python_files(root: Path, policy: dict[str, Any]) -> list[Path]:
    files: list[Path] = []
    for configured in _string_list(policy.get("paths")) or list(_DEFAULT_PATHS):
        base = root / configured
        if base.is_file() and base.suffix == ".py":
            files.append(base)
        elif base.exists():
            files.extend(sorted(base.rglob("*.py")))
    return [path for path in files if "__pycache__" not in path.parts]


def _suffix_module_findings(root: Path, policy: dict[str, Any]) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for path in _python_files(root, policy):
        if path.name == "__init__.py" or path.stem.startswith("_") or "_" not in path.stem:
            continue
        rel = path.relative_to(root).as_posix()
        gap = f"module_layout_suffix_module:{rel}:{path.stem}"
        findings.append({"gap": gap, "path": rel, "module": path.stem})
    return findings


def _suffix_group_findings(root: Path, policy: dict[str, Any]) -> list[dict[str, object]]:
    minimum = int(policy.get("suffix_flat_group_min", _DEFAULT_SUFFIX_GROUP_MIN))
    grouped: dict[Path, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for path in _python_files(root, policy):
        if path.name == "__init__.py" or path.stem.startswith("_") or "_" not in path.stem:
            continue
        prefix, _suffix = path.stem.split("_", maxsplit=1)
        grouped[path.parent.relative_to(root)][prefix].append(path.name)
    findings: list[dict[str, object]] = []
    for parent, groups in sorted(grouped.items()):
        parent_text = parent.as_posix()
        for prefix, names in sorted(groups.items()):
            if len(names) < minimum:
                continue
            gap = f"module_layout_suffix_flat:{parent_text}:{prefix}:{len(names)}"
            findings.append(
                {"gap": gap, "directory": parent_text, "prefix": prefix, "files": names}
            )
    return findings


def _flat_directory_findings(root: Path, policy: dict[str, Any]) -> list[dict[str, object]]:
    limit = int(policy.get("flat_directory_limit", _DEFAULT_FLAT_DIRECTORY_LIMIT))
    counts: dict[Path, int] = defaultdict(int)
    for path in _python_files(root, policy):
        if path.name != "__init__.py":
            counts[path.parent.relative_to(root)] += 1
    findings: list[dict[str, object]] = []
    for directory, count in sorted(counts.items()):
        directory_text = directory.as_posix()
        if count <= limit:
            continue
        gap = f"module_layout_flat_directory:{directory_text}:{count}>{limit}"
        findings.append({"gap": gap, "directory": directory_text, "module_count": count})
    return findings


def _private_alias_findings(root: Path, policy: dict[str, Any]) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for path in _python_files(root, policy):
        rel = path.relative_to(root).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                findings.extend(_import_private_aliases(rel, node.names))
            elif isinstance(node, ast.ImportFrom) and node.module:
                findings.extend(_from_import_private_aliases(rel, node.module, node.names))
    return findings


def _package_init_facade_findings(root: Path, policy: dict[str, Any]) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for path in _python_files(root, policy):
        if path.name != "__init__.py":
            continue
        rel = path.relative_to(root).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        reasons = _package_init_facade_reasons(tree)
        if not reasons:
            continue
        gap = f"module_layout_package_init_facade:{rel}"
        findings.append({"gap": gap, "path": rel, "reasons": reasons})
    return findings


def _package_init_facade_reasons(tree: ast.Module) -> list[str]:
    reasons: list[str] = []
    body = list(tree.body)
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    for node in body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            _append_reason(reasons, "import")
        elif _assigns_all(node):
            _append_reason(reasons, "explicit_exports")
        elif not isinstance(node, ast.Pass):
            _append_reason(reasons, "runtime_code")
    return reasons


def _assigns_all(node: ast.AST) -> bool:
    if isinstance(node, ast.Assign):
        return any(
            isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets
        )
    if isinstance(node, ast.AnnAssign):
        return isinstance(node.target, ast.Name) and node.target.id == "__all__"
    return False


def _append_reason(reasons: list[str], reason: str) -> None:
    if reason not in reasons:
        reasons.append(reason)


def _import_private_aliases(rel: str, aliases: list[ast.alias]) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for alias in aliases:
        if alias.asname and alias.asname.startswith("_"):
            gap = f"module_layout_private_import_alias:{rel}:{alias.name}->{alias.asname}"
            findings.append({"gap": gap, "path": rel, "source": alias.name, "alias": alias.asname})
    return findings


def _from_import_private_aliases(
    rel: str,
    module: str,
    aliases: list[ast.alias],
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for alias in aliases:
        if not alias.asname or not alias.asname.startswith("_"):
            continue
        source = f"{module}.{alias.name}"
        gap = f"module_layout_private_import_alias:{rel}:{source}->{alias.asname}"
        findings.append({"gap": gap, "path": rel, "source": source, "alias": alias.asname})
    return findings


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]
