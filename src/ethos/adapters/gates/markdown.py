"""Check exact document inputs with product-shipped native formatting and lint."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from pathlib import PurePosixPath
from tempfile import TemporaryDirectory
from typing import Annotated
from typing import Literal
from typing import TypedDict
from typing import overload

import yaml
from markdown_it import MarkdownIt
from pydantic import ConfigDict
from pydantic import Field
from pydantic import StrictBool
from pydantic import StrictStr
from pydantic import TypeAdapter
from pydantic import ValidationError
from pydantic import with_config

from ethos.adapters.process import run_command
from ethos.adapters.repo.content.observation import read_regular_bytes
from ethos.adapters.repo.content.source import SourceTree
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.runtime.materialization.input_resolution import resolve_node_runtime
from ethos.adapters.repo.runtime.materialization.native_supply import resolve_native_tool
from ethos.adapters.repo.runtime.materialization.node_package_supply import product_node_module
from ethos.contracts.paradigm.declaration import load_repository_paradigm
from ethos.repository.release.resources import canonical_resource


@with_config(ConfigDict(strict=True, extra="allow"))
class MarkdownFinding(TypedDict):
    """Retain native details while validating the selected finding identity."""

    fileName: StrictStr
    lineNumber: Annotated[int, Field(strict=True, ge=1)]
    ruleDescription: StrictStr
    ruleNames: Annotated[
        list[Annotated[str, Field(strict=True, min_length=1)]], Field(min_length=1)
    ]


@with_config(ConfigDict(strict=True, extra="forbid"))
class NativeDocumentPayload(TypedDict):
    """One finite native API response, not source or proof authority."""

    formatted: dict[str, StrictStr]
    findings: list[MarkdownFinding]
    lint_exit: Annotated[int, Field(strict=True, ge=0, le=1)]
    lint_reported: StrictBool
    diagnostics: list[StrictStr]


class NativeDocumentObservation(NativeDocumentPayload):
    """Bind the validated native response to its executed command."""

    command: list[str]
    stderr: str


class MarkdownFormatReport(TypedDict):
    """Nonmutating layout and lint evidence over one selected source tree."""

    id: str
    verdict: Literal["pass", "block"]
    file_count: int
    source_commit: str
    source_tree: str
    checked_paths: list[str]
    format_drift: list[str]
    findings: list[MarkdownFinding]
    command: list[str]
    native_diagnostics: list[str]
    required_gaps: list[str]


@with_config(ConfigDict(strict=True, extra="allow"))
class ProseFinding(TypedDict):
    """Native Vale coordinates, rule and meaning, with original details preserved."""

    Line: Annotated[int, Field(strict=True, ge=1)]
    Span: Annotated[
        list[Annotated[int, Field(strict=True, ge=1)]], Field(min_length=2, max_length=2)
    ]
    Check: Annotated[str, Field(strict=True, min_length=1)]
    Match: StrictStr
    Message: Annotated[str, Field(strict=True, min_length=1)]
    Severity: Literal["suggestion", "warning", "error"]


class MarkdownProseReport(TypedDict):
    """Native prose evidence over the same explicit source membership."""

    id: str
    verdict: Literal["pass", "block"]
    file_count: int
    source_commit: str
    source_tree: str
    checked_paths: list[str]
    findings: dict[str, list[ProseFinding]]
    command: list[str]
    exit_code: int
    state: str
    stdout: str
    stderr: str
    configuration: dict[str, object]
    required_gaps: list[str]


class WorkingMarkdownFormatReport(MarkdownFormatReport):
    """Authoring evidence cannot be mistaken for a committed format proof."""

    input_kind: Literal["working-tree"]


class WorkingMarkdownProseReport(MarkdownProseReport):
    """Authoring prose retains native diagnostics and its working-tree identity."""

    input_kind: Literal["working-tree"]


_DOCUMENT_PAYLOAD = TypeAdapter(NativeDocumentPayload)
_PROSE_PAYLOAD = TypeAdapter(dict[str, list[ProseFinding]])


def document_inputs(source: SourceTree) -> tuple[str, ...]:
    """Select every delivered Markdown member; immutability restricts writes, not lint."""
    paths = tuple(path for path in sorted(source.entries) if path.endswith(".md"))
    if not paths:
        message = "markdown_input_selection_empty"
        raise ValueError(message)
    return paths


def _document_selection(sources: dict[str, str], format_paths: tuple[str, ...] | None) -> None:
    """Bind one canonical relative namespace before any native input leaves the process."""
    if not sources:
        message = "markdown_input_selection_empty"
        raise ValueError(message)
    for name, body in sources.items():
        path = PurePosixPath(name)
        if (
            path.is_absolute()
            or not path.parts
            or any(part in {".", ".."} or ":" in part for part in path.parts)
            or path.as_posix() != name
            or "\\" in name
            or "\0" in name
            or not isinstance(body, str)
        ):
            message = "markdown_input_path_invalid"
            raise ValueError(message)
    if format_paths is not None and (
        not set(format_paths).issubset(sources) or len(set(format_paths)) != len(format_paths)
    ):
        message = "markdown_format_selection_invalid"
        raise ValueError(message)


def native_document_observation(
    root: Path,
    sources: dict[str, str],
    *,
    lint: bool = True,
    format_paths: tuple[str, ...] | None = None,
) -> NativeDocumentObservation:
    """Invoke native APIs over explicit finite strings, never candidate config or files."""
    _document_selection(sources, format_paths)
    prettier = product_node_module("prettier")
    markdownlint = product_node_module("markdownlint-cli2")
    settings = tomllib.loads(
        canonical_resource(".config/checks/prettier/prettier.toml").read_text(encoding="utf-8")
    )
    policy = yaml.safe_load(
        canonical_resource(".config/checks/markdownlint-cli2/.markdownlint-cli2.yaml").read_text(
            encoding="utf-8"
        )
    )
    with TemporaryDirectory(prefix="ethos-document-inputs-") as directory:
        request = {
            "sources": sources,
            "format_paths": list(sources if format_paths is None else format_paths),
            "settings": settings,
            "policy": policy,
            "lint": lint,
            "directory": directory,
        }
        result = run_command(
            root,
            (
                str(resolve_node_runtime().executable),
                str(Path(__file__).with_suffix(".mjs")),
                str(prettier / "package.json"),
                str(markdownlint / "package.json"),
            ),
            timeout=60,
            stdin=json.dumps(request),
            remove_env=("NODE_OPTIONS", "NODE_PATH"),
            remove_env_prefixes=("MISE_",),
        )
    if result.returncode != 0 or result.stderr:
        message = "markdown_native_execution_failed"
        raise ValueError(message + ":" + result.stderr.strip())
    try:
        observation = _DOCUMENT_PAYLOAD.validate_json(result.stdout)
    except ValidationError as error:
        message = "markdown_native_report_invalid"
        raise ValueError(message) from error
    if (
        set(observation["formatted"]) != set(sources)
        or type(observation["lint_exit"]) is not int
        or (lint and not observation["lint_reported"])
        or any(finding["fileName"] not in sources for finding in observation["findings"])
        or any(
            observation["formatted"][path] != body
            for path, body in sources.items()
            if format_paths is not None and path not in format_paths
        )
    ):
        message = "markdown_native_report_invalid"
        raise ValueError(message)
    return {**observation, "command": list(result.args), "stderr": result.stderr}


def markdown_format_report(root: Path) -> MarkdownFormatReport:
    """Check one exact committed source without rewriting governed documents."""
    source = SourceTree.observe(root)
    texts = {path: source.read(path).decode("utf-8") for path in document_inputs(source)}
    report = _format_report(source.root, texts, source.head, source.tree)
    source.recheck()
    return report


def _format_report(root: Path, texts: dict[str, str], head: str, tree: str) -> MarkdownFormatReport:
    """Use the same native formatter and lint floor for proof and authoring."""
    # Official OpenSpec owns artifact writes; native lint still checks those inputs.
    format_paths = tuple(
        path
        for path in texts
        if not path.startswith((*load_repository_paradigm().immutable_roots, "openspec/"))
    )
    observed = native_document_observation(root, texts, format_paths=format_paths)
    changed = [path for path in texts if observed["formatted"][path] != texts[path]]
    gaps = [f"markdown_format_drift:{path}" for path in changed]
    gaps += (
        ["markdown_lint_failed"]
        if observed["findings"] or observed["lint_exit"] or observed["diagnostics"]
        else []
    )
    return {
        "id": "markdown-format",
        "verdict": "block" if gaps else "pass",
        "file_count": len(texts),
        "source_commit": head,
        "source_tree": tree,
        "checked_paths": list(texts),
        "format_drift": changed,
        "findings": observed["findings"],
        "command": observed["command"],
        "native_diagnostics": observed["diagnostics"],
        "required_gaps": gaps,
    }


def markdown_prose_report(root: Path) -> MarkdownProseReport:
    """Check current committed prose with the shipped native Vale floor."""
    source = SourceTree.observe(root)
    texts = {
        path: source.read(path).decode("utf-8")
        for path in document_inputs(source)
        if not path.startswith(load_repository_paradigm().immutable_roots)
    }
    report = _prose_report(source.root, texts, source.head, source.tree)
    source.recheck()
    return report


def _prose_report(root: Path, texts: dict[str, str], head: str, tree: str) -> MarkdownProseReport:
    """Retain original native findings and exact selected identities without preprocessing."""
    _document_selection(texts, None)
    _require_native_prose_inputs(texts)
    executable = resolve_native_tool("vale")
    configuration = canonical_resource(".config/checks/vale/vale.ini")
    command = (
        str(executable),
        "--no-global",
        f"--config={configuration}",
        "--output=JSON",
        "--no-color",
    )
    native_policy = run_command(
        root, (*command, "ls-config"), timeout=20, remove_env_prefixes=("VALE_",)
    )
    if native_policy.returncode or native_policy.stderr:
        message = "markdown_prose_configuration_unavailable"
        raise ValueError(message + ":" + native_policy.stderr)
    policy = json.loads(native_policy.stdout)
    if not isinstance(policy, dict) or not policy:
        message = "markdown_prose_configuration_invalid"
        raise ValueError(message)
    findings: dict[str, list[ProseFinding]] = {}
    state = "checked"
    with TemporaryDirectory(prefix="ethos-prose-inputs-") as directory:
        selected = Path(directory)
        for path, text in texts.items():
            target = selected / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(text.encode("utf-8"))
        result = run_command(
            root,
            (*command, str(selected)),
            timeout=60,
            remove_env_prefixes=("VALE_",),
        )
        if type(result.returncode) is not int:
            state = "native_report_invalid"
        elif result.returncode not in (0, 1):
            state = "native_execution_failed"
        else:
            try:
                native = _PROSE_PAYLOAD.validate_json(result.stdout)
                findings = {
                    Path(path).relative_to(selected).as_posix(): rows
                    for path, rows in native.items()
                }
                _require_native_prose_result(texts, findings, result.returncode)
            except (ValidationError, ValueError):
                state = "native_report_invalid"
    failed = state != "checked" or bool(result.stderr) or any(findings.values())
    return {
        "id": "markdown-prose",
        "verdict": "block" if failed else "pass",
        "file_count": len(texts),
        "source_commit": head,
        "source_tree": tree,
        "checked_paths": list(texts),
        "findings": findings,
        "command": list(result.args),
        "exit_code": result.returncode,
        "state": state,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "configuration": {"command": list(native_policy.args), "policy": policy},
        "required_gaps": ["markdown_prose_failed"] if failed else [],
    }


def _require_native_prose_inputs(texts: dict[str, str]) -> None:
    """Native Markdown syntax distinguishes active controls from literal code examples."""
    markdown = MarkdownIt()
    for path, text in texts.items():
        html = (
            child.content
            for token in markdown.parse(text)
            for child in (token, *(token.children or ()))
            if child.type in {"html_block", "html_inline"}
        )
        if any(
            re.match(r"\s*vale(?:\s|$)", comment, re.IGNORECASE)
            for node in html
            for comment in re.findall(r"<!--(.*?)-->", node, re.DOTALL)
        ):
            message = f"markdown_prose_inline_policy_forbidden:{path}"
            raise ValueError(message)


def _require_native_prose_result(
    texts: dict[str, str], findings: dict[str, list[ProseFinding]], exit_code: int
) -> None:
    """Bind native findings to exact original lines and the original exit semantics."""
    if not set(findings).issubset(texts):
        message = "markdown_prose_report_invalid"
        raise ValueError(message)
    for path, rows in findings.items():
        lines = texts[path].splitlines()
        if any(
            row["Line"] > len(lines)
            or row["Span"][1] < row["Span"][0]
            or row["Span"][1] > len(lines[row["Line"] - 1])
            for row in rows
        ):
            message = "markdown_prose_report_invalid"
            raise ValueError(message)
    errors = any(row["Severity"] == "error" for rows in findings.values() for row in rows)
    if (exit_code == 1) != errors:
        message = "markdown_prose_report_invalid"
        raise ValueError(message)


def observe_working_documents(root: Path) -> dict[str, str]:
    """Observe complete native Git membership through bounded regular-file reads.

    This authoring capability includes nonignored candidate documents and keeps
    deleted members out. It conveys no committed-proof identity or write authority.
    """
    discovered = run_git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z")
    paths = sorted({path for path in discovered.stdout.split("\0") if path.endswith(".md")})
    texts = {}
    for path in paths:
        if not (root / path).exists() and not (root / path).is_symlink():
            continue
        content = read_regular_bytes(
            root,
            path,
            unsafe_gap=f"source_member_link_or_type_forbidden:{path}",
            unstable_gap=f"source_member_changed:{path}",
            size_gap=f"source_member_size_exceeded:{path}",
        )
        texts[path] = content.decode("utf-8")
    _document_selection(texts, None)
    return texts


@overload
def working_document_report(
    root: Path, *, kind: Literal["format"]
) -> WorkingMarkdownFormatReport: ...


@overload
def working_document_report(
    root: Path, *, kind: Literal["prose"]
) -> WorkingMarkdownProseReport: ...


def working_document_report(
    root: Path, *, kind: Literal["format", "prose"]
) -> WorkingMarkdownFormatReport | WorkingMarkdownProseReport:
    """Nonmutating native authoring check, explicitly not exact committed proof."""
    repo = root.resolve()
    head = current_tracked_head(repo)
    texts = observe_working_documents(repo)
    report: WorkingMarkdownFormatReport | WorkingMarkdownProseReport
    if kind == "prose":
        selected = {
            path: body
            for path, body in texts.items()
            if not path.startswith(load_repository_paradigm().immutable_roots)
        }
        report = {**_prose_report(repo, selected, head, ""), "input_kind": "working-tree"}
    else:
        report = {**_format_report(repo, texts, head, ""), "input_kind": "working-tree"}
    if current_tracked_head(repo) != head or observe_working_documents(repo) != texts:
        message = "document_authoring_source_changed"
        raise ValueError(message)
    return report
