"""Read the gate registry ETHOS's own profile names, beside the shared packaged registry."""

from __future__ import annotations

import tomllib
from pathlib import Path

from ethos.contracts.gates import Gate
from ethos.contracts.gates import GateRegistryDeclaration
from ethos.contracts.gates import load_gate_registry_declaration

ROOT = Path(__file__).resolve().parents[2]


def repository_registry_path() -> Path:
    """Return the registry file ETHOS's committed profile declares for its own gates."""
    profile = tomllib.loads((ROOT / ".ethos/profile.toml").read_text(encoding="utf-8"))
    return ROOT / profile["proof"]["gate_registry"]


def repository_registry() -> GateRegistryDeclaration:
    """Load ETHOS's own gates exactly as its profile declares them."""
    return load_gate_registry_declaration(repository_registry_path())


def proof_registry() -> dict[str, Gate]:
    """Name every gate ETHOS's proof can select: the shared obligations and its own gates."""
    return load_gate_registry_declaration().registry() | repository_registry().registry()
