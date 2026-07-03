"""System-contract loader — makes system/*.toml load-bearing.

Reads the machine governance kernel's declarative contracts off disk so downstream
code DERIVES behavior from the contract instead of hardcoding it (tao First
Principle #5). Lives in ethos-contracts (the layer permitted TOML IO); the kernel
stays a pure leaf (ethos-contracts must not import ethos_core per the pure-leaf
contract), so the contract-name list is owned here.
"""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

# The machine governance kernel's declarative contracts under system/.
SYSTEM_CONTRACTS = (
    "authority",
    "formats",
    "routing",
    "surfaces",
    "tools",
    "workflows",
    "evidence_boundaries",
)


def load_system_contract(root: Path, name: str) -> dict[str, object]:
    """Load system/<name>.toml as a dict. Raises FileNotFoundError when absent."""
    path = root / "system" / f"{name}.toml"
    return tomllib.loads(path.read_text(encoding="utf-8"))


def system_contracts_report(root: Path) -> dict[str, object]:
    """Load every declared system contract and report load gaps (derive-not-store).

    A gap here means the machine governance kernel's contract surface is missing or
    malformed — a blocking condition, because downstream derivation reads from it.
    """
    loaded: dict[str, bool] = {}
    gaps: list[str] = []
    for name in SYSTEM_CONTRACTS:
        path = root / "system" / f"{name}.toml"
        if not path.exists():
            loaded[name] = False
            gaps.append(f"system_contract_missing:{name}")
            continue
        try:
            tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            loaded[name] = False
            gaps.append(f"system_contract_invalid:{name}:{exc}")
        else:
            loaded[name] = True
    return {
        "ok": not gaps,
        "contracts": loaded,
        "required_gaps": gaps,
    }
