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
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit
from urllib.request import url2pathname

from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.process import run_command
from ethos.adapters.repo.content.observation import observed_document_origins
from ethos.adapters.repo.content.source import SourceTargetUnavailableError
from ethos.adapters.repo.content.source import SourceTree
from ethos.adapters.repo.git import GitExecutionError
from ethos.adapters.repo.git import git_files
from ethos.adapters.repo.runtime.materialization.input_resolution import resolve_node_runtime
from ethos.adapters.repo.runtime.materialization.node_package_supply import product_node_module
from ethos.contracts.verdict import close_verdict
from ethos.normalization.coercion import string_sequence
from ethos.repository.policy.layout.report import module_layout_report
from ethos.repository.policy.projections import observe_projections
from ethos.repository.policy.quality.tool_configuration import native_tool_configuration
from ethos.repository.registry.docs.registry import authored_document_paths
from ethos.repository.registry.docs.registry import build_docs_registry
from ethos.repository.release.resources import canonical_resource


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
    files: list[str] = []
    try:
        source = SourceTree.observe(root)
        root = source.root
        files = sorted(path for path in source.entries if path.endswith(".md"))
        for relative in files:
            source.resolve_target(relative)
        files = _markdown_files(root, selected_paths=tuple(source.entries))
        configs = native_configurations(root, "lychee", ".config/checks/lychee/lychee.toml")
        tool = str(
            Path(sys.executable).absolute().with_name("lychee.exe" if os.name == "nt" else "lychee")
        )
        _require_link_inputs(files, tool)
        native = []
        for index, config in enumerate(configs):
            configuration = Path(config)
            if configuration.is_relative_to(source.root):
                source.read(configuration.relative_to(source.root).as_posix())
            command = (
                tool,
                "--config",
                config,
                "--no-progress",
                "--no-ignore",
                "--hidden",
                "--offline=false" if online else "--offline",
            )
            inputs = tuple(str(source.root / relative) for relative in files)
            _require_native_link_selection(source.root, command, inputs)
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
            if not online:
                dumped = run_command(
                    source.root, (*command, *mode, "--dump", "--", *inputs), timeout=60
                )
                _require_native_link_output(dumped)
                _qualify_local_targets(source, dumped.stdout)
            result = run_command(source.root, (*command, *mode, "--", *inputs), timeout=90)
            gaps = (
                []
                if result.returncode == 0 and not result.stderr.strip()
                else [f"quality_gate_failed:{gate_id}"]
            )
            native.append(
                {
                    "verdict": "block" if gaps else "pass",
                    "id": gate_id if index == 0 else f"{gate_id}-increment",
                    "tool": tool,
                    "state": "failed" if gaps else "passed",
                    "file_count": len(files),
                    "command": list(result.args),
                    "exit_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "required_gaps": gaps,
                }
            )
        source.recheck()
    except (GitExecutionError, subprocess.CalledProcessError) as error:
        return quality_inventory_failure(root, gate_id, error)
    except SourceTargetUnavailableError as error:
        return _link_observation_failure(gate_id, files, "block", str(error))
    except (
        OSError,
        ValueError,
        UnicodeError,
        ProcessExecutionError,
        subprocess.SubprocessError,
    ) as error:
        return _link_observation_failure(gate_id, files, "unknown", str(error))
    return {**_native_report(gate_id, files, native), "source_tree": source.tree}


def _require_link_inputs(files: list[str], tool: str) -> None:
    if not files:
        message = "markdown_link_source_empty"
        raise ValueError(message)
    if shutil.which(tool) is None:
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
            root, (*command, "--dump-inputs", "--", *group), text=False, timeout=60
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


def quality_source_files(root: Path, *patterns: str) -> list[str]:
    """Read current authored input through native Git without swallowing inventory failure."""
    return git_files(
        root, "--cached", "--others", "--exclude-standard", "--", *patterns, check=True
    )


def quality_inventory_failure(
    root: Path, gate_id: str, error: GitExecutionError | subprocess.CalledProcessError
) -> dict[str, object]:
    """Unavailable input remains unknown with its original native execution evidence."""
    evidence = (
        error.evidence()
        if isinstance(error, GitExecutionError)
        else {
            "command": list(error.cmd),
            "cwd": str(root),
            "exit_code": error.returncode,
            "stdout": _observed_output(error.stdout),
            "stderr": _observed_output(error.stderr),
        }
    )
    return {
        "id": gate_id,
        "verdict": "unknown",
        "state": "inventory_unavailable",
        "file_count": 0,
        "required_gaps": [f"quality_input_inventory_unavailable:{gate_id}"],
        "errors": [evidence],
    }


def _markdown_files(root: Path, *, selected_paths: tuple[str, ...] | None = None) -> list[str]:
    """Current authored Markdown excludes immutable records and absent paths."""
    files = (
        quality_source_files(root, "*.md")
        if selected_paths is None
        else [path for path in selected_paths if path.endswith(".md")]
    )
    outputs = frozenset(item.output for item in observe_projections(root))
    registry = build_docs_registry(
        root,
        generated_outputs=outputs,
        retained_origins=observed_document_origins(root),
        selected_documents=tuple(files),
    )
    return [
        path
        for path in authored_document_paths(registry, files, outputs)
        if selected_paths is not None or (root / path).is_file()
    ]


def native_configurations(root: Path, tool: str, shared: str) -> tuple[str, ...]:
    """The shipped policy is mandatory; repository policy is a native increment."""
    common = canonical_resource(shared)
    selected = native_tool_configuration(tuple(quality_source_files(root)), tool)
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


def prose_report(root: Path) -> dict[str, object]:
    """Run native spelling on exact copies without ambient policy or source writes."""
    try:
        files = _markdown_files(root)
        configs = native_configurations(
            root, "codespell", ".config/checks/codespell/codespell.toml"
        )
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


def format_source_contents(root: Path, owner: str, sources: dict[str, bytes]) -> dict[str, bytes]:
    """Render literal source copies in one native batch, without source writes.

    Product policy remains mandatory. A repository increment must have the same
    fixed point; conflicting native policies refuse rather than oscillate.
    """
    if not sources:
        return {}
    node = str(resolve_node_runtime().executable)
    if owner == "prettier":
        executable = str(product_node_module(owner) / "bin/prettier.cjs")
        configs = native_configurations(root, owner, ".config/checks/prettier/prettier.toml")
        options = ("--write", "--no-editorconfig", "--ignore-path", os.devnull)
    elif owner == "taplo":
        executable = str(product_node_module("@taplo/cli") / "dist/cli.js")
        configs = native_configurations(root, owner, ".config/checks/taplo/taplo.toml")
        options = ("format", "--no-auto-config", "--colors", "never")
    else:
        message = f"native_format_owner_unsupported:{owner}"
        raise ValueError(message)
    with TemporaryDirectory(prefix="ethos-native-format-") as temporary:
        work = Path(temporary)
        for relative, content in sources.items():
            target = work / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        rendered: dict[str, bytes] = {}
        for ordinal, config in enumerate(configs):
            command = (node, executable, *options, "--config", config)
            if owner == "prettier":
                command += ("--print-width", "100", "--prose-wrap", "preserve")
            command += tuple(str(work / relative) for relative in sources)
            try:
                completed = run_command(
                    work,
                    command,
                    timeout=120,
                    remove_env=("NODE_OPTIONS", "NODE_PATH", "TAPLO_CONFIG"),
                )
            except (OSError, ProcessExecutionError, subprocess.TimeoutExpired) as error:
                message = f"native_format_unavailable:{owner}:{error}"
                raise ValueError(message) from error
            if completed.returncode:
                message = completed.stderr or completed.stdout
                message = f"native_format_failed:{owner}:{message.strip()}"
                raise ValueError(message)
            observed = {relative: (work / relative).read_bytes() for relative in sources}
            if ordinal and observed != rendered:
                message = f"native_format_policy_conflict:{owner}"
                raise ValueError(message)
            rendered = observed
        return rendered


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
            return {
                "verdict": "pass",
                "state": "skipped",
                "file_count": 0,
                "required_gaps": [],
            }
        node = str(resolve_node_runtime().executable)
        prettier = str(product_node_module("prettier") / "bin/prettier.cjs")
        markdownlint = str(product_node_module("markdownlint-cli2") / "markdownlint-cli2.mjs")
        format_configs = native_configurations(
            root, "prettier", ".config/checks/prettier/prettier.toml"
        )
        lint_configs = native_configurations(
            root,
            "markdownlint-cli2",
            ".config/checks/markdownlint-cli2/.markdownlint-cli2.yaml",
        )
    except (GitExecutionError, subprocess.CalledProcessError) as error:
        return quality_inventory_failure(root, "markdown-lint", error)
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
        (
            "markdown-lint",
            [node, adapter, markdownlint, config, str(root), json.dumps(files)],
        )
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
    try:
        files = tuple(
            root / path for path in quality_source_files(root, "*.py") if (root / path).is_file()
        )
    except (GitExecutionError, subprocess.CalledProcessError) as error:
        return quality_inventory_failure(root, "module-layout", error)
    return module_layout_report(root, files=files)
