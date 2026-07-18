from __future__ import annotations

from typing import cast

import ethos.adapters.repo.git as git_adapter
from ethos.adapters.gates.tool import quality_tool_report
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import resolve_root
from ethos_core.result import EthosResult


def emit_quality_tool_result(**kwargs) -> None:
    """Run a quality-tool adapter report and emit its CLI result."""
    report = quality_tool_report(
        root=kwargs["root"],
        gate_id=kwargs["gate_id"],
        tool=kwargs["tool"],
        command=list(kwargs["command"]),
        files=list(kwargs["files"]),
    )
    result = EthosResult(
        command=kwargs["result_command"],
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(cast("list[str]", report["required_gaps"])),
        data=report,
    )
    emit(result, json_output=kwargs["json_output"], enforce=False)


def compile_quality_tool_handlers(*, declarations, import_path_prefix=None) -> dict:
    """Compile declared quality-tool commands from the canonical registry."""
    return {
        declaration.import_path.rsplit(":", maxsplit=1)[1]: _tool_handler(declaration)
        for declaration in declarations
        if declaration.tool_handler is not None
        and (import_path_prefix is None or declaration.import_path.startswith(import_path_prefix))
    }


def _tool_handler(declaration):
    handler = declaration.tool_handler

    def command(*, root: RootOption | None = None, json_output: JsonFlag = False) -> None:
        repo = resolve_root(root)
        files = tuple(
            dict.fromkeys(
                path
                for pattern in handler.file_globs
                for path in _files(repo, pattern)
                if not path.startswith(handler.exclude_prefixes)
            )
        )
        emit_quality_tool_result(
            root=repo,
            gate_id=handler.gate_id,
            tool=handler.tool,
            command=[*handler.command, *(files if handler.append_files else ())],
            files=files,
            result_command=f"{declaration.group} {declaration.name}",
            json_output=json_output,
        )

    return command


def _files(root, pattern):
    return git_adapter.git_files(root, pattern) or ([pattern] if (root / pattern).is_file() else [])
