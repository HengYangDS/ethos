"""Quality-tool IO adapter — runs an external quality tool and reports its result.

The impure execution layer: shells out to a formatter/linter binary. Domain/surface
receive the structured report and stay free of subprocess concerns.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.process import run_command
from ethos.adapters.repo.git import git_files
from ethos.adapters.repo.runtime.materialization.input_resolution import resolve_node_runtime
from ethos.adapters.repo.runtime.materialization.node_package_supply import product_node_module
from ethos.contracts.verdict import close_verdict
from ethos.normalization.coercion import string_sequence
from ethos.repository.policy.layout.report import module_layout_report
from ethos.repository.policy.quality.tool_configuration import native_tool_configuration
from ethos.repository.release.resources import canonical_resource


def _trim_output(text: str, *, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}\n[trimmed {len(text) - limit} bytes]"


def quality_tool_report(
    *,
    root: Path,
    gate_id: str,
    tool: str,
    command: list[str],
    files: list[str],
) -> dict[str, object]:
    """Run an external quality tool over files and structure its pass/fail result."""
    if not files:
        return {
            "verdict": "pass",
            "id": gate_id,
            "tool": tool,
            "state": "skipped",
            "file_count": 0,
            "required_gaps": [],
        }
    if shutil.which(tool) is None:
        return {
            "verdict": "unknown",
            "id": gate_id,
            "tool": tool,
            "state": "missing_tool",
            "file_count": len(files),
            "command": command,
            "required_gaps": [f"quality_tool_missing:{tool}"],
        }
    # Fixed gate command (list form, no shell, no external input).
    try:
        completed = run_command(
            root,
            tuple(command),
            timeout=120,
            remove_env=("NODE_OPTIONS", "NODE_PATH"),
        )
    except (OSError, ProcessExecutionError, subprocess.TimeoutExpired) as error:
        return {
            "verdict": "unknown",
            "id": gate_id,
            "tool": tool,
            "state": "tool_error",
            "file_count": len(files),
            "command": command,
            "error": f"{type(error).__name__}: {error}",
            "required_gaps": [f"quality_tool_execution_unknown:{gate_id}"],
        }
    gaps = [] if completed.returncode == 0 else [f"quality_gate_failed:{gate_id}"]
    return {
        "verdict": close_verdict(
            "pass" if completed.returncode == 0 else "block",
            required_gaps=tuple(gaps),
        ),
        "id": gate_id,
        "tool": tool,
        "state": "passed" if completed.returncode == 0 else "failed",
        "file_count": len(files),
        "command": command,
        "exit_code": completed.returncode,
        "stdout": _trim_output(completed.stdout),
        "stderr": _trim_output(completed.stderr),
        "required_gaps": gaps,
    }


def markdown_links_report(root: Path) -> dict[str, object]:
    """Check repository-local links and anchors without network access."""
    return _lychee_report(root, gate_id="markdown-links", online=False)


def external_links_report(root: Path) -> dict[str, object]:
    """Check HTTP and HTTPS links from a network-capable proof host."""
    return _lychee_report(root, gate_id="external-links", online=True)


def _lychee_report(root: Path, *, gate_id: str, online: bool) -> dict[str, object]:
    files = _markdown_files(root)
    try:
        configs = _native_configurations(root, "lychee", ".config/checks/links/lychee.toml")
    except (OSError, ValueError) as error:
        return _configuration_failure(gate_id, error)
    mode = ["--offline=false", "--scheme", "http", "--scheme", "https"] if online else []
    tool = str(
        Path(sys.executable).absolute().with_name("lychee.exe" if os.name == "nt" else "lychee")
    )
    native = [
        quality_tool_report(
            root=root,
            gate_id=gate_id if index == 0 else f"{gate_id}-increment",
            tool=tool,
            command=[tool, "--config", config, "--no-progress", *mode, *files],
            files=files,
        )
        for index, config in enumerate(configs)
    ]
    return _native_report(gate_id, files, native)


def _markdown_files(root: Path) -> list[str]:
    """Current authored Markdown excludes immutable records and absent tracked paths."""
    return [
        path
        for path in git_files(root, "*.md")
        if path.endswith(".md")
        and not path.startswith(("evidence/", "docs/archive/", "openspec/changes/archive/"))
        and (root / path).is_file()
    ]


def _native_configurations(root: Path, tool: str, shared: str) -> tuple[str, ...]:
    """The shipped policy is mandatory; repository policy is a native increment."""
    common = canonical_resource(shared)
    selected = native_tool_configuration(tuple(git_files(root)), tool)
    if selected:
        path = root / selected
        if (
            path.is_symlink()
            or not path.resolve().is_relative_to(root.resolve())
            or not path.is_file()
        ):
            message = f"native_tool_configuration_invalid:{tool}"
            raise ValueError(message)
        if path.resolve() != common.resolve():
            return str(common), str(path)
    return (str(common),)


def _configuration_failure(gate_id: str, error: Exception) -> dict[str, object]:
    return {
        "id": gate_id,
        "verdict": "block",
        "state": "configuration_invalid",
        "required_gaps": [str(error)],
    }


def markdown_lint_report(root: Path) -> dict[str, object]:
    """Check the shared floor and native repository increments on the same authored inputs."""
    files = _markdown_files(root)
    if not files:
        return {"verdict": "pass", "state": "skipped", "file_count": 0, "required_gaps": []}
    try:
        node = str(resolve_node_runtime().executable)
        prettier = str(product_node_module("prettier") / "bin/prettier.cjs")
        markdownlint = str(product_node_module("markdownlint-cli2") / "markdownlint-cli2.mjs")
        format_configs = _native_configurations(
            root, "prettier", ".config/checks/format/prettier.toml"
        )
        lint_configs = _native_configurations(
            root, "markdownlint-cli2", ".config/checks/markdown/markdownlint.yaml"
        )
    except (OSError, ValueError) as error:
        return _configuration_failure("markdown-lint", error)
    commands = [
        (
            "markdown-format",
            [
                node,
                prettier,
                "--config",
                config,
                "--no-editorconfig",
                "--prose-wrap",
                "preserve",
                "--ignore-path",
                os.devnull,
                "--check",
                "--",
                *files,
            ],
        )
        for config in format_configs
    ]
    adapter = str(Path(__file__).with_name("markdown.mjs"))
    commands.extend(
        ("markdown-lint", [node, adapter, markdownlint, config, str(root), json.dumps(files)])
        for config in lint_configs
    )
    native = [
        quality_tool_report(root=root, gate_id=gate_id, tool=node, command=command, files=files)
        for gate_id, command in commands
    ]
    return _native_report("markdown-lint", files, native)


def _native_report(
    gate_id: str, files: list[str], native: list[dict[str, object]]
) -> dict[str, object]:
    gaps = [gap for result in native for gap in string_sequence(result["required_gaps"])]
    return {
        "id": gate_id,
        "verdict": close_verdict("pass", required_gaps=tuple(gaps)),
        "state": "verified" if not gaps else "unproven",
        "file_count": len(files),
        "required_gaps": gaps,
        "native": native,
    }


def module_layout_gate_report(root: Path) -> dict[str, object]:
    """Audit tracked and non-ignored untracked Python through the layout policy."""
    files = tuple(
        root / path
        for path in git_files(root, "--cached", "--others", "--exclude-standard", "--", "*.py")
        if (root / path).is_file()
    )
    return module_layout_report(root, files=files)
