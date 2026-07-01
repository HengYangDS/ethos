from __future__ import annotations

KERNEL_CHAIN = (
    "JudgmentSource",
    "Subject",
    "Commitment",
    "Change",
    "Evidence",
    "Claim",
    "Chronicle",
)


def kernel_chain() -> tuple[str, ...]:
    return KERNEL_CHAIN
