from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

KERNEL_CHAIN = (
    "JudgmentSource",
    "Subject",
    "Commitment",
    "Change",
    "Evidence",
    "Claim",
    "Chronicle",
)

TRANSITION_COMMANDS = (
    "ethos status",
    "ethos plan",
    "ethos prove",
    "ethos land",
    "ethos publish",
)

SCORECARD_COMMANDS = ("ethos report",)


def governance_context(root: Path, *, profile: str) -> dict[str, object]:
    return {
        "contract": "governed_repository",
        "profile": profile,
        "subject": {
            "kind": "repository",
            "root": str(root.resolve()),
        },
        "single_kernel": True,
        "kernel_chain": list(KERNEL_CHAIN),
        "shared_commands": list(TRANSITION_COMMANDS),
        "transition_commands": list(TRANSITION_COMMANDS),
        "scorecard_commands": list(SCORECARD_COMMANDS),
        "truth_boundary": "repository",
        "profile_boundary": "profile_or_adapter",
    }
