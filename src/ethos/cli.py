"""ETHOS CLI entrypoint."""

from __future__ import annotations

import sys

from ethos.adapters.repo.git import GitExecutionError
from ethos.contracts.admission import root_command
from ethos.result import EthosResult
from ethos.surface.cli.application import app
from ethos.surface.cli.application import dispatch_arguments
from ethos.surface.cli.application import load_command_groups
from ethos.surface.cli.output import emit
from ethos.surface.cli.output import emit_git_execution_failure
from ethos.surface.cli.output import emit_invalid_repository_profile


def main() -> None:
    """Run the ETHOS CLI."""
    argv = sys.argv[1:]
    try:
        load_command_groups(argv)
        app(dispatch_arguments(argv))
    except GitExecutionError as exc:
        emit_git_execution_failure(
            command=root_command(argv) or "ethos",
            code=exc.code,
            reason=exc.reason,
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
    emit(
        EthosResult(
            command=command,
            verdict="block",
            state="gapped",
            required_gaps=(gap,),
            next_action="repair the reported gap and rerun the command",
            data={"error_boundary": "public_command_contract"},
        ),
        json_output="--json" in argv,
        enforce=True,
    )


if __name__ == "__main__":
    main()
