from __future__ import annotations

from pathlib import Path
from typing import Any

import ethos.adapters.shadow.execution as shadow_execution
import ethos.adapters.shadow.identity as shadow_identity
import ethos.adapters.shadow.semantics as shadow_semantics
from ethos.repository.evidence.parity.validation import SHADOW_COMMAND_ARGS

# The read-only shadow command set is defined once in the repository layer
# (SHADOW_COMMAND_ARGS) so the executed commands and the parity-evidence display
# strings cannot drift. Aliased here for the local execution call sites.
READ_ONLY_COMMANDS = SHADOW_COMMAND_ARGS


def run_shadow_parity(
    target: Path,
    *,
    timeout_seconds: int = 30,
    product_root: Path | None = None,
) -> dict[str, Any]:
    target = target.resolve()
    product_root = (product_root or Path.cwd()).resolve()
    comparisons = []
    required_gaps: list[str] = []
    for command in READ_ONLY_COMMANDS:
        external = shadow_execution.run_external(target, command, timeout_seconds=timeout_seconds)
        embedded = shadow_execution.run_embedded(target, command, timeout_seconds=timeout_seconds)
        external_json = external.get("json", {})
        embedded_json = embedded.get("json", {})
        diff = shadow_semantics.semantic_diff(command, external_json, embedded_json)
        false_negative_gaps = shadow_semantics.false_negative_gaps(
            command,
            external_json,
            embedded_json,
        )
        accepted_differences = shadow_semantics.accepted_semantic_differences(
            command,
            external_json,
            embedded_json,
        )
        command_label = "ethos " + " ".join(command)
        if shadow_execution.process_failed(external):
            required_gaps.append(f"external_command_failed:{' '.join(command)}")
        for gap in _list(embedded.get("required_gaps")):
            if str(gap) not in required_gaps:
                required_gaps.append(str(gap))
        if shadow_execution.process_failed(embedded):
            required_gaps.append(f"embedded_command_failed:{' '.join(command)}")
        if false_negative_gaps:
            required_gaps.append(f"shadow_false_negative:{' '.join(command)}")
        if diff:
            required_gaps.append(f"shadow_diff:{' '.join(command)}")
        comparisons.append(
            {
                "command": command_label,
                "external": external,
                "embedded": embedded,
                "semantic_diff": diff,
                "false_negative_gaps": false_negative_gaps,
                "accepted_summary": shadow_semantics.accepted_summary(accepted_differences),
                "accepted_differences": accepted_differences,
            }
        )
    identity = shadow_identity.identity_envelope(
        target,
        READ_ONLY_COMMANDS,
        product_root=product_root,
        comparisons=comparisons,
    )
    return {
        "ok": not required_gaps,
        "state": "matched" if not required_gaps else "different",
        "target": target.as_posix(),
        "identity": identity,
        "required_gaps": required_gaps,
        "accepted_summary": shadow_semantics.accepted_summary(
            difference
            for comparison in comparisons
            for difference in comparison["accepted_differences"]
        )
        | {
            "command_count": sum(
                1 for comparison in comparisons if comparison["accepted_differences"]
            )
        },
        "false_negative_count": sum(
            len(comparison["false_negative_gaps"]) for comparison in comparisons
        ),
        "comparisons": comparisons,
        "execution_packages": [
            execution_package(gap=gap, target=target, comparisons=comparisons)
            for gap in required_gaps
        ],
    }


def execution_package(
    *,
    gap: str,
    target: Path,
    comparisons: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "gap": gap,
        "state": "failed",
        "target": target.as_posix(),
        "commands": [str(comparison["command"]) for comparison in comparisons],
        "semantic_dimensions": list(shadow_semantics.SEMANTIC_DIMENSIONS),
        "blocking": True,
        "next_action": "inspect shadow parity comparison output",
    }


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
