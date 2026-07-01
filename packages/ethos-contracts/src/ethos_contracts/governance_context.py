from __future__ import annotations

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

SCORECARD_COMMANDS = (
    "ethos report",
)


def governance_context(root: Path, *, posture: str, profile: str) -> dict[str, object]:
    return {
        "contract": "single_kernel_dual_posture",
        "posture": posture,
        "profile": profile,
        "subject": {
            "kind": "repository",
            "role": posture,
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
