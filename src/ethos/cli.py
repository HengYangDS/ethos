"""ETHOS CLI entrypoint."""

from __future__ import annotations

import shlex
import sys
from pathlib import Path

from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.repo.git import GitExecutionError
from ethos.adapters.repo.git import repository_root
from ethos.adapters.store.state.schema import state_schema_report
from ethos.contracts.admission import root_command
from ethos.result import EthosResult
from ethos.surface.cli.application import app
from ethos.surface.cli.application import dispatch_arguments
from ethos.surface.cli.application import load_command_groups
from ethos.surface.cli.output import emit
from ethos.surface.cli.output import emit_git_execution_failure
from ethos.surface.cli.output import emit_invalid_repository_profile
from ethos.surface.cli.output import emit_process_execution_failure
from ethos.surface.cli.version import version_text


def main() -> None:
    """Run the ETHOS CLI."""
    argv = sys.argv[1:]
    if "--version" in argv:
        sys.stdout.write(f"{version_text()}\n")
        return
    try:
        load_command_groups(argv)
        app(dispatch_arguments(argv))
    except GitExecutionError as exc:
        emit_git_execution_failure(
            command=root_command(argv) or "ethos",
            error=exc,
            json_output="--json" in argv,
        )
    except ProcessExecutionError as exc:
        emit_process_execution_failure(
            command=root_command(argv) or "ethos",
            error=exc,
            json_output="--json" in argv,
        )
    except ValueError as exc:
        if str(exc) == "repository_profile_invalid:.ethos/profile.toml":
            _emit_invalid_profile(root_command(argv) or "ethos", argv)
        else:
            _emit_contract_failure(root_command(argv) or "ethos", argv, exc)
    except RuntimeError as exc:
        _emit_contract_failure(root_command(argv) or "ethos", argv, exc)


def _emit_invalid_profile(command: str, argv: list[str]) -> None:
    """Emit the stable structured invalid-profile result for one public command."""
    emit_invalid_repository_profile(
        command=command,
        json_output="--json" in argv,
        enforce=command == "prove" or (command in {"land", "publish"} and "--apply" in argv),
    )


def _emit_contract_failure(command: str, argv: list[str], error: Exception) -> None:
    """Close one public contract failure without leaking a traceback."""
    gap = str(error).strip() or "public_command_contract_failure"
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
    emit(
        EthosResult(
            command=command,
            verdict="block",
            state="gapped",
            required_gaps=(gap,),
            next_action=_contract_failure_action(gap, root, schema),
            data=data,
        ),
        json_output="--json" in argv,
        enforce=True,
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


if __name__ == "__main__":
    main()
