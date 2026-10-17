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
import tomllib
from pathlib import Path
from tempfile import TemporaryDirectory

import ethos.adapters.gates.native.inputs as native_inputs
from ethos.adapters.gates.formatting import render_source_content
from ethos.adapters.gates.native.inputs import native_configurations
from ethos.adapters.gates.native.inputs import quality_inventory_failure
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.process import run_command
from ethos.adapters.repo.git import GitExecutionError
from ethos.adapters.repo.runtime.materialization.input_resolution import resolve_node_runtime
from ethos.adapters.repo.runtime.materialization.node_package_supply import product_node_module
from ethos.contracts.verdict import close_verdict
from ethos.normalization.coercion import string_sequence
from ethos.repository.policy.layout.report import module_layout_report


def _observed_output(value: str | bytes | None) -> str:
    """Preserve observed text, including native timeout streams returned as bytes."""
    return value.decode(errors="replace") if isinstance(value, bytes) else value or ""


def quality_tool_report(
    *,
    root: Path,
    gate_id: str,
    tool: str,
    command: list[str],
    files: list[str],
    cwd: Path | None = None,
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
    if tool != sys.executable and shutil.which(tool) is None:
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
            cwd or root,
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
            "exit_code": None,
            "stdout": _observed_output(error.stdout)
            if isinstance(error, subprocess.TimeoutExpired)
            else "",
            "stderr": _observed_output(error.stderr)
            if isinstance(error, subprocess.TimeoutExpired)
            else "",
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
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "required_gaps": gaps,
    }


def markdown_links_report(root: Path) -> dict[str, object]:
    """Check repository-local links and anchors without network access."""
    return _lychee_report(root, gate_id="markdown-links", online=False)


def external_links_report(root: Path) -> dict[str, object]:
    """Check HTTP and HTTPS links from a network-capable proof host."""
    return _lychee_report(root, gate_id="external-links", online=True)


def _lychee_report(root: Path, *, gate_id: str, online: bool) -> dict[str, object]:
    try:
        files = _markdown_files(root)
        configs = native_configurations(root, "lychee", ".config/checks/lychee/lychee.toml")
    except (GitExecutionError, subprocess.CalledProcessError) as error:
        return quality_inventory_failure(root, gate_id, error)
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
    """Use the common authored-input join while preserving absent-path filtering."""
    return [
        path
        for path in native_inputs.authored_source_files(root, "*.md")
        if path.endswith(".md") and (root / path).is_file()
    ]


def prose_report(root: Path) -> dict[str, object]:
    """Run native spelling on exact copies without ambient policy or source writes."""
    try:
        files = _markdown_files(root)
        configs = native_configurations(
            root, "codespell", ".config/checks/codespell/codespell.toml"
        )
        for config in configs:
            settings = tomllib.loads(Path(config).read_text(encoding="utf-8")).get("tool")
            if not isinstance(settings, dict) or not isinstance(settings.get("codespell"), dict):
                message = f"codespell_configuration_table_missing:{config}"
                return _configuration_failure("prose", ValueError(message))
        sources = {relative: (root / relative).read_bytes() for relative in files}
        if any((root / relative).is_symlink() for relative in files):
            return _configuration_failure("prose", ValueError("native_prose_input_invalid"))
        native = []
        for ordinal, config in enumerate(configs):
            with TemporaryDirectory(prefix="ethos-native-prose-") as temporary:
                work = Path(temporary)
                for relative, content in sources.items():
                    target = work / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(content)
                command = [
                    sys.executable,
                    "-B",
                    "-I",
                    "-m",
                    "codespell_lib",
                    "--toml",
                    config,
                    "--count",
                    "--quiet-level=2",
                    *files,
                ]
                result = quality_tool_report(
                    root=root,
                    gate_id="prose" if ordinal == 0 else "prose-increment",
                    tool=sys.executable,
                    command=command,
                    files=files,
                    cwd=work,
                )
                if files and (
                    not str(result.get("stderr", "")).strip().isdecimal()
                    or any(
                        (work / relative).read_bytes() != content
                        for relative, content in sources.items()
                    )
                ):
                    result.update(verdict="block", state="unproven")
                    result["required_gaps"] = [
                        *string_sequence(result["required_gaps"]),
                        "native_prose_not_read_only_clean",
                    ]
                native.append(result)
        return _native_report("prose", files, native)
    except (GitExecutionError, subprocess.CalledProcessError) as error:
        return quality_inventory_failure(root, "prose", error)
    except (OSError, ValueError) as error:
        return _configuration_failure("prose", error)


def _configuration_failure(gate_id: str, error: Exception) -> dict[str, object]:
    return {
        "id": gate_id,
        "verdict": "block",
        "state": "configuration_invalid",
        "required_gaps": [str(error)],
    }


def markdown_lint_report(root: Path) -> dict[str, object]:
    """Check the shared floor and native repository increments on the same authored inputs."""
    try:
        files = _markdown_files(root)
        if not files:
            return {"verdict": "pass", "state": "skipped", "file_count": 0, "required_gaps": []}
        node = str(resolve_node_runtime().executable)
        markdownlint = str(product_node_module("markdownlint-cli2") / "markdownlint-cli2.mjs")
        lint_configs = native_configurations(
            root, "markdownlint-cli2", ".config/checks/markdownlint-cli2/.markdownlint-cli2.yaml"
        )
    except (GitExecutionError, subprocess.CalledProcessError) as error:
        return quality_inventory_failure(root, "markdown-lint", error)
    except (OSError, ValueError) as error:
        return _configuration_failure("markdown-lint", error)
    format_gaps = []
    try:
        for relative in files:
            content = (root / relative).read_bytes()
            rendered, _ignored = render_source_content(root, relative, "prettier", content)
            if rendered != content:
                format_gaps.append(f"source_format_drift:{relative}")
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        format_gaps.append(str(error))
    format_report: dict[str, object] = {
        "id": "markdown-format",
        "verdict": "block" if format_gaps else "pass",
        "state": "failed" if format_gaps else "passed",
        "required_gaps": format_gaps,
        "files": files,
        "file_count": len(files),
    }
    commands = []
    adapter = str(Path(__file__).with_name("markdown.mjs"))
    commands.extend(
        ("markdown-lint", [node, adapter, markdownlint, config, str(root), json.dumps(files)])
        for config in lint_configs
    )
    native = [
        format_report,
        *[
            quality_tool_report(root=root, gate_id=gate_id, tool=node, command=command, files=files)
            for gate_id, command in commands
        ],
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
    try:
        files = tuple(
            root / path
            for path in native_inputs.quality_source_files(root, "*.py")
            if (root / path).is_file()
        )
    except (GitExecutionError, subprocess.CalledProcessError) as error:
        return quality_inventory_failure(root, "module-layout", error)
    return module_layout_report(root, files=files)
