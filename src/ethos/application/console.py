"""Run one ETHOS console invocation: select its runtime, bound its command, close its failures.

`ethos.cli` keeps the entry points and hands this module its `main` and an emitter that resolves
the output surface only when called, so the console loads no surface module and `ethos --version`
imports no Cyclopts. The console also owns the root a command resolved, whose store receives the
oversized detail of its result.
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from contextlib import contextmanager
from contextlib import nullcontext
from contextvars import ContextVar
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Protocol

from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.process import command_scope
from ethos.adapters.repo.git import GitExecutionError
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import repository_root
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.invocation_facts import invocation_scope
from ethos.adapters.repo.runtime.interpreter import PYTHON_FLAGS
from ethos.adapters.repo.runtime.selection import current_runtime
from ethos.adapters.repo.runtime.selection import runtime_inspection_scope
from ethos.adapters.store.state.schema import state_schema_report
from ethos.application.invocation import process_failure_result
from ethos.application.invocation import profile_failure_result
from ethos.contracts.admission import root_command
from ethos.contracts.operations.catalog import select_argv
from ethos.contracts.outcome import outcome_of
from ethos.repository.paradigm.parameters import repository_parameters
from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.result import EthosResult

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Generator

# The root a command resolved; its oversized result detail belongs in that repository's store.
_RESOLVED_ROOT: ContextVar[Path | None] = ContextVar("ethos_resolved_root", default=None)


class Emit(Protocol):
    """Render one result for the console, with the exit its enforcement asks for."""

    def __call__(self, result: EthosResult, *, json_output: bool, enforce: bool) -> None: ...


def resolve_root(root: Path | None) -> Path:
    """Resolve an explicit path or the containing Git worktree root."""
    candidate = (root or Path.cwd()).resolve()
    completed = run_git(candidate, "rev-parse", "--show-toplevel", check=False)
    if completed.returncode == 0 and completed.stdout.strip():
        candidate = Path(completed.stdout.strip()).resolve()
    _RESOLVED_ROOT.set(candidate)
    return candidate


def resolved_root() -> Path | None:
    """Return the root this invocation's command resolved, if it resolved one."""
    return _RESOLVED_ROOT.get()


def run_console(argv: list[str], main: Callable[[], None]) -> EthosResult | None:
    """Run `main` under the target repository's selected runtime, re-executing into it if needed.

    Returns the failure to emit when selecting that runtime fails; `main` emits its own results.
    """
    command = "version" if "--version" in argv else root_command(argv) or "ethos"
    try:
        target = _argument_root(argv)
        if (
            _creates_root(argv)
            or (command == "mcp" and "--create-target" in argv)
            or not target.exists()
        ):
            main()
            return None
        common = git_common_dir(target)
        selector = Path(common) / "ethos/runtime/CURRENT"
        if (
            common
            and argv[:2] != ["hook", "install"]
            and (selector.exists() or selector.is_symlink())
        ):
            selected = current_runtime(Path(common))
            if Path(sys.executable).absolute() != selected.python.absolute():
                executable = str(selected.python)
                commandline = [executable, *PYTHON_FLAGS, "-m", "ethos.cli", *argv]
                if sys.platform == "win32":
                    raise SystemExit(subprocess.run(commandline, check=False).returncode)
                os.execv(executable, commandline)
                return None
            if command == "status":
                with runtime_inspection_scope(Path(common), selected):
                    main()
                return None
    except ProcessExecutionError as exc:
        return process_failure_result(command, exc, root=_argument_root(argv))
    except (OSError, ValueError) as exc:
        return _contract_failure(command, argv, exc)
    main()
    return None


@contextmanager
def command_boundary(command: str, argv: list[str], emit: Emit) -> Generator[None]:
    """Run one command in its process scope and close each of its failures as a result."""
    json_output = "--json" in argv
    with command_scope(handle_termination=True):
        try:
            yield
        except ProcessExecutionError as exc:
            emit(
                process_failure_result(command, exc, root=_argument_root(argv)),
                json_output=json_output,
                enforce=True,
            )
        except ValueError as exc:
            if str(exc) == INVALID_PROFILE_ERROR:
                # An unselected root argv exits as a refusal would, and a group command keeps 0.
                selected = select_argv(["ethos", *argv])
                emit(
                    profile_failure_result(command, _argument_root(argv)),
                    json_output=json_output,
                    enforce=selected is not None
                    and (selected[1] is None or selected[1].exit == "verdict"),
                )
            else:
                emit(_contract_failure(command, argv, exc), json_output=json_output, enforce=True)
        except RuntimeError as exc:
            emit(_contract_failure(command, argv, exc), json_output=json_output, enforce=True)


@contextmanager
def invocation_parameters(command: str, argv: list[str]) -> Generator[None]:
    """Bind the target repository's parameters and one invocation's fact scope to a command.

    Every command observes an immutable fact once; the MCP server serves many requests, so it
    keeps no invocation scope of its own.
    """
    invocation = nullcontext() if command == "mcp" else invocation_scope()
    with repository_parameters(_argument_root(argv)), invocation:
        yield


def _creates_root(argv: list[str]) -> bool:
    """Return whether the argv selects an operation that forms its root instead of binding one."""
    selected = select_argv(["ethos", *argv])
    return selected is not None and selected[1] is not None and selected[1].creates_root


def _contract_failure(command: str, argv: list[str], error: Exception) -> EthosResult:
    """Close one public contract failure with every gap it carries, without a traceback."""
    outcome = outcome_of(error, fallback="public_command_contract_failure")
    gap = outcome.gaps[0]
    root = _argument_root(argv)
    data: dict[str, object] = {"error_boundary": "public_command_contract"}
    schema: dict[str, object] | None = None
    if gap.startswith("state_schema_"):
        try:
            schema = state_schema_report(repository_root(root))
        except (GitExecutionError, OSError, ValueError):
            schema = {
                "expected_state": "current",
                "observed_state": "unavailable",
            }
        data["state_schema"] = schema
    return EthosResult.from_outcome(
        command, outcome, next_action=_contract_failure_action(gap, root, schema), data=data
    )


def _argument_root(argv: list[str]) -> Path:
    if "--root" in argv:
        index = argv.index("--root")
        if index + 1 < len(argv):
            return Path(argv[index + 1]).resolve()
    value = next((item.partition("=")[2] for item in argv if item.startswith("--root=")), "")
    return Path(value).resolve() if value else Path.cwd().resolve()


def _contract_failure_action(
    gap: str,
    root: Path,
    schema: dict[str, object] | None,
) -> str:
    if not gap.startswith("state_schema_"):
        return "repair the reported gap and rerun the command"
    command = ["ethos", "hook", "install", "--root", root.as_posix()]
    observed = str((schema or {}).get("observed_state") or "")
    if observed not in {"absent", "current", "legacy"} and gap != "state_schema_migration_required":
        command.extend(("--reset-state", "--authorize"))
    command.append("--json")
    return shlex.join(command)
