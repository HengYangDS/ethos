"""Quality-tool IO adapter — runs an external quality tool and reports its result.

The impure execution layer: shells out to a formatter/linter binary. Domain/surface
receive the structured report and stay free of subprocess concerns.
"""

from __future__ import annotations

import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit
from urllib.request import url2pathname

from markdown_it import MarkdownIt

import ethos.adapters.gates.native.inputs as native_inputs
from ethos.adapters.gates.formatting import render_source_content
from ethos.adapters.gates.native.inputs import native_configurations
from ethos.adapters.gates.native.inputs import quality_inventory_failure
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.process import run_command
from ethos.adapters.repo.content.source import SourceTargetUnavailableError
from ethos.adapters.repo.content.source import SourceTree
from ethos.adapters.repo.git import GitExecutionError
from ethos.adapters.repo.runtime.filesystem import runtime_scripts
from ethos.adapters.repo.runtime.materialization.input_resolution import resolve_node_runtime
from ethos.adapters.repo.runtime.materialization.native_supply import resolve_native_tool
from ethos.adapters.repo.runtime.materialization.node_package_supply import product_node_module
from ethos.contracts.verdict import close_verdict
from ethos.normalization.coercion import string_sequence
from ethos.repository.policy.layout.report import module_layout_report
from ethos.repository.release.resources import canonical_resource

_MARKDOWN = MarkdownIt("commonmark")
_VALE_CONTROL = re.compile(r"<!--\s*vale\s")


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
    """Check delivered members with mandatory installed policy and native increments."""
    files: list[str] = []
    try:
        source = SourceTree.observe(root)
        files = sorted(
            native_inputs.authored_source_files(
                root,
                "*.md",
                paths=tuple(relative for relative in source.entries if relative.endswith(".md")),
            )
        )
        for relative in files:
            source.resolve_target(relative)
        configs = native_configurations(root, "lychee", ".config/checks/lychee/lychee.toml")
        product_root = canonical_resource()
        for config in configs:
            path = Path(config).resolve()
            if path.is_relative_to(source.root) and not (
                product_root != source.root and path.is_relative_to(product_root)
            ):
                source.read(path.relative_to(source.root).as_posix())
        tool = runtime_scripts(Path(sys.prefix)) / ("lychee.exe" if os.name == "nt" else "lychee")
        _require_link_inputs(files, tool)
        inputs = tuple(str(source.root / relative) for relative in files)
        literal = _native_link_inputs(inputs)
        mode = (
            ("--scheme", "http", "--scheme", "https")
            if online
            else (
                "--scheme",
                "file",
                "--include",
                "^file:",
                "--include-fragments=anchor-only",
                "--base-url",
                "",
                "--remap",
                "^(.*)$ $1",
            )
        )
        native = []
        for index, config in enumerate(configs):
            command = (
                str(tool),
                "--config",
                config,
                "--no-progress",
                "--no-ignore",
                "--hidden",
                "--offline=false" if online else "--offline",
            )
            _require_native_link_selection(source.root, command, inputs)
            # Lychee writes UTF-8 on every platform, not the Windows ANSI code page.
            if not online:
                dumped = run_command(
                    source.root,
                    (*command, *mode, "--dump", "--", *literal),
                    output_encoding="utf-8",
                    timeout=60,
                )
                _require_native_link_output(dumped)
                _qualify_local_targets(source, dumped.stdout)
            result = run_command(
                source.root, (*command, *mode, "--", *literal), output_encoding="utf-8", timeout=90
            )
            gaps = (
                []
                if result.returncode == 0 and not result.stderr.strip()
                else [f"quality_gate_failed:{gate_id}"]
            )
            native.append(
                {
                    "verdict": "block" if gaps else "pass",
                    "id": gate_id if index == 0 else f"{gate_id}-increment",
                    "tool": str(tool),
                    "state": "failed" if gaps else "passed",
                    "file_count": len(files),
                    "command": list(result.args),
                    "exit_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "required_gaps": gaps,
                    "source_tree": source.tree,
                }
            )
        source.recheck()
        return {**_native_report(gate_id, files, native), "source_tree": source.tree}
    except SourceTargetUnavailableError as error:
        return _link_observation_failure(gate_id, files, "block", str(error))
    except (GitExecutionError, subprocess.CalledProcessError) as error:
        return quality_inventory_failure(root, gate_id, error)
    except (OSError, ValueError, ProcessExecutionError, subprocess.SubprocessError) as error:
        return _link_observation_failure(gate_id, files, "unknown", str(error))


def _require_link_inputs(files: list[str], tool: Path) -> None:
    """Require complete selected inputs and the exact installed executable."""
    if not files:
        message = "markdown_link_source_empty"
        raise ValueError(message)
    if not tool.is_file() or not os.access(tool, os.X_OK):
        message = "quality_tool_missing:lychee"
        raise ValueError(message)


def _require_native_link_selection(
    root: Path, command: tuple[str, ...], inputs: tuple[str, ...]
) -> None:
    """Bind native line-framed output to whole input identities without guessing splits."""
    ordinary = tuple(path for path in inputs if len(path.splitlines()) == 1)
    groups = ((ordinary,) if ordinary else ()) + tuple(
        (path,) for path in inputs if len(path.splitlines()) != 1
    )
    for group in groups:
        selected = run_command(
            root,
            (*command, "--dump-inputs", "--", *_native_link_inputs(group)),
            text=False,
            timeout=60,
        )
        _require_native_link_output(selected)
        expected = tuple(os.fsencode(path) for path in group)
        matches = (
            selected.stdout == expected[0] + b"\n"
            if len(group) == 1
            else sorted(selected.stdout.splitlines()) == sorted(expected)
        )
        if not matches:
            message = "markdown_link_input_selection_unproven"
            raise ValueError(message)


def _native_link_inputs(paths: tuple[str, ...]) -> tuple[str, ...]:
    """Escape glob syntax, which Lychee interprets in inputs, so each path names itself."""
    return tuple(glob.escape(path) for path in paths)


def _require_native_link_output(result: subprocess.CompletedProcess[str | bytes]) -> None:
    if result.returncode or result.stderr.strip():
        message = "markdown_link_extraction_unproven"
        raise ValueError(message)


def _qualify_local_targets(source: SourceTree, output: str) -> None:
    """Native Lychee owns URI syntax; the shared observer owns delivered membership."""
    for line in output.splitlines():
        url = urlsplit(line.strip())
        if url.scheme != "file":
            message = "markdown_link_extraction_unproven"
            raise ValueError(message)
        if url.netloc not in {"", "localhost"}:
            message = "source_target_nonlocal_file"
            raise SourceTargetUnavailableError(message)
        target = Path(url2pathname(url.path))
        try:
            relative = target.relative_to(source.root).as_posix()
        except ValueError as error:
            message = "source_target_outside_root"
            raise SourceTargetUnavailableError(message) from error
        source.resolve_target(relative)


def _link_observation_failure(
    gate_id: str, files: list[str], verdict: str, reason: str
) -> dict[str, object]:
    return {
        "verdict": verdict,
        "id": gate_id,
        "tool": "lychee",
        "state": "unavailable" if verdict == "block" else "unproven",
        "file_count": len(files),
        "required_gaps": [reason],
        "diagnostics": [{"reason": reason}],
    }


def _markdown_files(root: Path) -> list[str]:
    """Use the common authored-input join while preserving absent-path filtering."""
    return [
        path
        for path in native_inputs.authored_source_files(root, "*.md")
        if path.endswith(".md") and (root / path).is_file()
    ]


def prose_report(root: Path) -> dict[str, object]:
    """Run native spelling and Vale on exact copies without ambient policy or source writes.

    Authored text that Git classifies as binary is refused before any native tool reads it.
    """
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
        authored = native_inputs.authored_text_report(root, files)
        if authored["required_gaps"]:
            return _native_report("prose", files, [authored])
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
        native.extend(_vale_reports(root, files, sources))
        return _native_report("prose", files, native)
    except (GitExecutionError, subprocess.CalledProcessError) as error:
        return quality_inventory_failure(root, "prose", error)
    except (OSError, ValueError) as error:
        return _configuration_failure("prose", error)


def _vale_controls(sources: dict[str, bytes]) -> list[str]:
    """Locate each Vale comment control, which would weaken the shared floor; code stays text."""
    return [
        f"native_prose_control_refused:{relative}:{(token.map or [0])[0] + 1}"
        for relative, content in sources.items()
        for token in _MARKDOWN.parse(content.decode("utf-8"))
        for item in (token, *(token.children or ()))
        if item.type in {"html_block", "html_inline"} and _VALE_CONTROL.search(item.content)
    ]


def _vale_reports(
    root: Path, files: list[str], sources: dict[str, bytes]
) -> list[dict[str, object]]:
    """Run the shipped Vale policy, then any repository policy, on exact copies."""
    configs = native_configurations(root, "vale", ".config/checks/vale/vale.ini")
    executable = str(resolve_native_tool("vale"))
    controls, reports = _vale_controls(sources), []
    for ordinal, config in enumerate(configs):
        with TemporaryDirectory(prefix="ethos-native-vale-") as temporary:
            work = Path(temporary)
            for relative, content in sources.items():
                target = work / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
            result = quality_tool_report(
                root=root,
                gate_id="prose-vale" if ordinal == 0 else "prose-vale-increment",
                tool=executable,
                command=[executable, "--no-global", f"--config={config}", "--output=line", *files],
                files=files,
                cwd=work,
            )
            if files and (
                str(result.get("stderr", "")).strip()
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
            if ordinal == 0 and controls:
                result.update(verdict="block", state="unproven")
                result["required_gaps"] = [*string_sequence(result["required_gaps"]), *controls]
            reports.append(result)
    return reports


def _configuration_failure(gate_id: str, error: Exception) -> dict[str, object]:
    return {
        "id": gate_id,
        "verdict": "block",
        "state": "configuration_invalid",
        "required_gaps": [str(error)],
    }


def markdown_lint_report(root: Path) -> dict[str, object]:
    """Check the shared floor and native repository increments on the same authored inputs.

    Authored text that Git classifies as binary is refused before any native tool reads it.
    """
    try:
        files = _markdown_files(root)
        if not files:
            return {"verdict": "pass", "state": "skipped", "file_count": 0, "required_gaps": []}
        authored = native_inputs.authored_text_report(root, files)
        if authored["required_gaps"]:
            return _native_report("markdown-lint", files, [authored])
        node = str(resolve_node_runtime().executable)
        markdownlint = str(product_node_module("markdownlint-cli2") / "markdownlint-cli2.mjs")
        lint_configs = native_configurations(
            root, "markdownlint-cli2", ".config/checks/markdownlint-cli2/.markdownlint-cli2.yaml"
        )
    except (GitExecutionError, subprocess.CalledProcessError) as error:
        return quality_inventory_failure(root, "markdown-lint", error)
    except (OSError, ValueError) as error:
        return _configuration_failure("markdown-lint", error)
    format_gaps: list[str] = []
    formatted: tuple[tuple[str, str], ...] = ()
    try:
        formatted = _native_formatter_owners(root, files)
        for relative, owner in formatted:
            content = (root / relative).read_bytes()
            rendered, _ignored = render_source_content(root, relative, owner, content, node=node)
            if rendered != content:
                format_gaps.append(f"source_format_drift:{relative}")
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as error:
        format_gaps.append(str(error))
    format_report: dict[str, object] = {
        "id": "markdown-format",
        "verdict": "block" if format_gaps else "pass",
        "state": "failed" if format_gaps else "passed",
        "required_gaps": format_gaps,
        "files": [relative for relative, _owner in formatted],
        "file_count": len(formatted),
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


def _native_formatter_owners(root: Path, files: list[str]) -> tuple[tuple[str, str], ...]:
    """Check only declared native-formatter carriers; official owners keep their own bytes."""
    ownership = native_inputs.format_ownership(root, tuple(files))
    if ownership["verdict"] != "pass":
        raise ValueError(str(ownership["failures"]))
    return tuple(
        (item["path"], item["format_owner"])
        for item in ownership["assignments"]
        if item["mutation_policy"] == "native-formatter"
    )


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
