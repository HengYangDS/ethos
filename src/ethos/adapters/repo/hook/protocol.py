"""Native Git hook protocol with demand-driven admission and no CLI dependency."""

from __future__ import annotations

import json
import subprocess
import sys
from functools import partial
from importlib import import_module
from pathlib import Path
from typing import IO

from ethos.adapters.repo.git import repository_root
from ethos.adapters.repo.hook.binding import HOOK_NAMES
from ethos.contracts.verdict import report_verdict

_ZERO_OIDS = {"0" * 40, "0" * 64}


def execute_hook(root: Path, name: str, args: tuple[str, ...], *, stdin: IO[str]) -> int:
    """Parse one native invocation and load authority only for required admission."""
    repo = root.resolve()
    try:
        if name not in HOOK_NAMES:
            reports = (blocked_report(name, "hook_name_invalid"),)
        elif name == "reference-transaction":
            reports = _reference_transaction(repo, args, stdin)
        else:
            admission = import_module("ethos.adapters.repo.hook.admission")
            reports = admission.admit_hook(repo, name, args, stdin=stdin)
    except (OSError, RuntimeError, TypeError, ValueError, ImportError) as error:
        reports = (blocked_report(name, str(error) or error.__class__.__name__),)
    failed = next((report for report in reports if report_verdict(report) != "pass"), None)
    if failed is not None:
        try:
            output = json.dumps(
                failed,
                sort_keys=True,
                allow_nan=False,
                default=lambda value: import_module("ethos.contracts.value").mutable_json(value),
            )
        except (TypeError, ValueError, RecursionError):
            output = json.dumps(blocked_report(name, "hook_report_not_json_native"), sort_keys=True)
        sys.stderr.write(output + "\n")
        return 1
    return 0


def _reference_transaction(
    root: Path, args: tuple[str, ...], stdin: IO[str]
) -> tuple[dict[str, object], ...]:
    """Consume Git notifications without importing unused admission machinery."""
    phase = args[0] if args else ""
    if phase not in {"prepared", "committed", "aborted"}:
        return (passed_report("reference-transaction", "phase_not_governed"),)
    reports = []
    admit = None
    for line in stdin:
        fields = line.split()
        if len(fields) != 3:
            reports.append(blocked_report("reference-transaction", "ref_update_invalid"))
            continue
        old_value, new_value, ref_name = fields
        if not ref_name.startswith("refs/heads/") or (
            old_value == new_value and old_value not in _ZERO_OIDS
        ):
            continue
        if phase != "prepared":
            reports.append(passed_report("reference-transaction", f"{phase}_observed"))
            continue
        if admit is None:
            admission = import_module("ethos.adapters.repo.hook.admission")
            admit = partial(
                admission.admit_reference,
                selected_runtime=admission.current_runtime(Path(admission.git_common_dir(root))),
            )
        reports.append(admit(root, ref_name, old_value, new_value))
    return tuple(reports) or (passed_report("reference-transaction", "no_governed_updates"),)


def passed_report(hook: str, state: str) -> dict[str, object]:
    """Return the native hook success envelope, not mutation authority."""
    return {"verdict": "pass", "state": state, "hook": hook, "required_gaps": []}


def blocked_report(hook: str, gap: str, *, branch: str = "") -> dict[str, object]:
    """Retain the rejected native hook boundary and exact required gap."""
    return {
        "verdict": "block",
        "state": "blocked",
        "hook": hook,
        "branch": branch,
        "decision": {"action": "block", "reason": gap},
        "required_gaps": [gap],
    }


def main() -> None:
    """Consume Git's positional hook protocol from the package-selected launcher."""
    name, *arguments = sys.argv[1:] or [""]
    try:
        root = repository_root(Path.cwd()) if name in HOOK_NAMES else Path.cwd()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        sys.stderr.write(json.dumps(blocked_report(name, str(error)), sort_keys=True) + "\n")
        raise SystemExit(1) from error
    raise SystemExit(execute_hook(root, name, tuple(arguments), stdin=sys.stdin))


if __name__ == "__main__":
    main()
