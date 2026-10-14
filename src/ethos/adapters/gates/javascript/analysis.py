"""Inspect selected JavaScript with product-pinned native ESLint, never candidate config."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from pathlib import PurePosixPath

from ethos.adapters.process import run_command
from ethos.adapters.repo.runtime.materialization.input_resolution import resolve_node_runtime
from ethos.adapters.repo.runtime.materialization.node_package_supply import product_node_module

ENVIRONMENT_POLICY = ".config/checks/eslint/policy.toml"
# Standard global sets a repository may declare for code that runs outside Node, such as
# callbacks a test driver evaluates in a browser page.
DECLARABLE_ENVIRONMENTS = frozenset({"browser", "serviceworker", "worker"})


def declared_environments(root: Path) -> dict[str, tuple[str, ...]]:
    """Read the declared execution environments, validating every name and path."""
    policy = root / ENVIRONMENT_POLICY
    if not policy.is_file():
        return {}
    message = "javascript_environment_policy_invalid"
    try:
        entries = tomllib.loads(policy.read_text(encoding="utf-8")).get("environment")
    except (tomllib.TOMLDecodeError, UnicodeError) as error:
        raise ValueError(message) from error
    if not isinstance(entries, list) or not entries:
        raise ValueError(message)
    environments: dict[str, tuple[str, ...]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"paths", "globals", "reason"}:
            raise ValueError(message)
        paths, names, reason = entry["paths"], entry["globals"], entry["reason"]
        if (
            not isinstance(reason, str)
            or not reason.strip()
            or not isinstance(names, list)
            or not names
            or not set(names) <= DECLARABLE_ENVIRONMENTS
            or not isinstance(paths, list)
            or not paths
        ):
            raise ValueError(message)
        for path in paths:
            relative = PurePosixPath(path) if isinstance(path, str) else None
            if (
                relative is None
                or relative.is_absolute()
                or ".." in relative.parts
                or not (root / relative).is_file()
                or path in environments
            ):
                raise ValueError(message)
            environments[path] = tuple(sorted(names))
    return environments


def _source_type(root: Path, relative: str) -> str:
    path = root / relative
    if path.suffix == ".mjs":
        return "module"
    if path.suffix == ".cjs":
        return "commonjs"
    for parent in path.parents:
        manifest = parent / "package.json"
        if manifest.is_file():
            mode = json.loads(manifest.read_text(encoding="utf-8")).get("type", "commonjs")
            if mode not in {"module", "commonjs"}:
                message = "javascript_package_type_invalid"
                raise ValueError(message)
            return mode
        if parent == root:
            break
    return "commonjs"


def static_observation(
    root: Path,
    paths: tuple[str, ...],
    *,
    node: str | None = None,
    native: dict[str, str] | None = None,
) -> dict[str, object]:
    """Run one finite native lexical check over exact clean source inputs."""
    if not (root / "package.json").is_file():
        message = "javascript_package_missing"
        raise ValueError(message)
    environments = declared_environments(root)
    entries = [
        {
            "path": path,
            "source": (root / path).read_text(encoding="utf-8"),
            "sourceType": _source_type(root, path),
            "environments": list(environments.get(path, ())),
        }
        for path in paths
    ]
    supply = product_node_module("eslint")
    result = run_command(
        root,
        (
            node or str(resolve_node_runtime().executable),
            str(Path(__file__).with_suffix(".mjs")),
            str(supply / "package.json"),
        ),
        timeout=60,
        stdin=json.dumps(entries),
        remove_env=("NODE_OPTIONS", "NODE_PATH"),
        env=native,
        remove_env_prefixes=("MISE_",),
    )
    reports = json.loads(result.stdout)
    if (
        not isinstance(reports, list)
        or len(reports) != len(paths)
        or any(
            not isinstance(report, dict)
            or not isinstance(report.get("messages"), list)
            or not isinstance(report.get("errorCount"), int)
            or not isinstance(report.get("warningCount"), int)
            or (root / path).resolve() != Path(str(report.get("filePath"))).resolve()
            for path, report in zip(paths, reports, strict=True)
        )
    ):
        message = "javascript_static_report_invalid"
        raise ValueError(message)
    if any(
        (root / entry["path"]).read_text(encoding="utf-8") != entry["source"] for entry in entries
    ):
        message = "javascript_static_source_changed"
        raise ValueError(message)
    failed = (
        result.returncode != 0
        or bool(result.stderr)
        or any(
            report["errorCount"] or report["warningCount"] or report["messages"]
            for report in reports
        )
    )
    return {
        "language": "javascript",
        "tool": "eslint",
        "verdict": "block" if failed else "pass",
        "checked_paths": len(paths),
        "environments": {path: list(names) for path, names in sorted(environments.items())},
        "reports": reports,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.returncode,
    }
