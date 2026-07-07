"""Kernel constants — the canonical governance chain.

Pure kernel: names only, zero IO. The system-contract loader and its contract-name
list live in ethos-contracts (the layer permitted TOML IO), so the kernel stays a
pure leaf.
"""

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
