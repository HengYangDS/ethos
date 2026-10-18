"""Quality-tool IO adapter — runs an external quality tool and reports its result.

The impure execution layer: shells out to a formatter/linter binary. Domain/surface
receive the structured report and stay free of subprocess concerns.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import url2pathname

from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.process import run_command
from ethos.adapters.repo.content.source import SourceTargetUnavailableError
from ethos.adapters.repo.content.source import SourceTree
from ethos.adapters.repo.git import git_files
from ethos.contracts.paradigm.declaration import load_repository_paradigm
from ethos.contracts.verdict import close_verdict
from ethos.repository.policy.layout.report import module_layout_report


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
        completed = subprocess.run(
            command,
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as error:
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
    files: list[str] = []
    try:
        source = SourceTree.observe(root)
        files = sorted(
            path
            for path in source.entries
            if path.endswith(".md") and not path.startswith(("evidence/", "docs/archive/"))
        )
        for relative in files:
            source.resolve_target(relative)
        carrier = load_repository_paradigm().native_carrier("lychee.toml")
        source.read(carrier)
        _require_link_inputs(files)
        command = (
            "lychee",
            "--config",
            carrier,
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
        source.recheck()
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
    gaps = (
        []
        if result.returncode == 0 and not result.stderr.strip()
        else [f"quality_gate_failed:{gate_id}"]
    )
    return {
        "verdict": "block" if gaps else "pass",
        "id": gate_id,
        "tool": "lychee",
        "state": "failed" if gaps else "passed",
        "file_count": len(files),
        "command": list(result.args),
        "exit_code": result.returncode,
        "stdout": _trim_output(result.stdout),
        "stderr": _trim_output(result.stderr),
        "required_gaps": gaps,
        "source_tree": source.tree,
    }


def _require_link_inputs(files: list[str]) -> None:
    if not files:
        message = "markdown_link_source_empty"
        raise ValueError(message)
    if shutil.which("lychee") is None:
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


def module_layout_gate_report(root: Path) -> dict[str, object]:
    """Audit tracked and non-ignored untracked Python through the layout policy."""
    files = tuple(
        root / path
        for path in git_files(root, "--cached", "--others", "--exclude-standard", "--", "*.py")
        if (root / path).is_file()
    )
    return module_layout_report(root, files=files)
