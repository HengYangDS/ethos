"""Inspect selected JavaScript with product-pinned native ESLint, never candidate config."""

from __future__ import annotations

import json
from pathlib import Path

from ethos.adapters.process import run_command
from ethos.adapters.repo.runtime.materialization.input_resolution import resolve_node_executable
from ethos.adapters.repo.runtime.materialization.node_package_supply import product_node_module


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
    entries = [
        {
            "path": path,
            "source": (root / path).read_text(encoding="utf-8"),
            "sourceType": _source_type(root, path),
        }
        for path in paths
    ]
    supply = product_node_module("eslint")
    result = run_command(
        root,
        (
            node or str(resolve_node_executable()),
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
        "reports": reports,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.returncode,
    }
