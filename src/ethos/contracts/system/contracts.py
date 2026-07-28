"""System-contract loader — makes system/*.toml load-bearing.

Reads the machine governance kernel's declarative contracts off disk so downstream
code derives behavior from the contract instead of hardcoding it. This loader
lives in ethos-contracts, the layer permitted TOML IO; the kernel stays a pure
leaf, so the contract-name list is owned here.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import jsonschema

from ethos._resources import declaration_text

# The machine governance kernel's declarative contracts under system/.
RESOURCE_BACKED_SYSTEM_CONTRACTS = {"lifecycle": "data/lifecycle.toml"}

SYSTEM_CONTRACTS = (
    "authority",
    "formats",
    "routing",
    "surfaces",
    "tools",
    "lifecycle",
    "evidence_boundaries",
    "invalid_states",
)


def load_system_contract(root: Path, name: str) -> dict[str, object]:
    """Load system/<name>.toml, falling back to product resources when declared.

    Most system contracts are root-owned and must fail closed when missing. The
    lifecycle declaration is product-owned so adopters compile the same TransitionPlan
    and transition policies without copying product repository files.
    """
    path = root / "system" / f"{name}.toml"
    if path.exists():
        return tomllib.loads(path.read_text(encoding="utf-8"))
    resource = RESOURCE_BACKED_SYSTEM_CONTRACTS.get(name)
    if resource:
        text = declaration_text(path, resource=resource, canonical=Path("system") / f"{name}.toml")
        return tomllib.loads(text)
    return tomllib.loads(path.read_text(encoding="utf-8"))


def schema_validation_gaps(name: str, payload: dict[str, object], schema_path: Path) -> list[str]:
    """Validate a contract against its declared JSON schema."""
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.validate(payload, schema)
    except jsonschema.ValidationError as exc:
        return [f"system_contract_schema_violation:{name}:{exc.message[:80]}"]
    except (ValueError, OSError) as exc:
        return [f"system_schema_unreadable:{name}:{exc}"]
    return []


def system_contracts_report(root: Path) -> dict[str, object]:
    """Load every declared system contract, validate its schema ref exists, report gaps.

    A gap means the machine governance kernel's contract surface is missing, malformed,
    or claims a schema that does not exist — all blocking, because downstream
    derivation reads from these contracts and a decorative `schema=` ref is an
    unenforced claim (the reference must bind, not decorate).
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
            payload = tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            loaded[name] = False
            gaps.append(f"system_contract_invalid:{name}:{exc}")
            continue
        loaded[name] = True
        schema_ref = payload.get("schema")
        if isinstance(schema_ref, str) and schema_ref:
            schema_path = root / schema_ref
            if not schema_path.exists():
                gaps.append(f"system_schema_ref_missing:{name}:{schema_ref}")
            else:
                gaps.extend(schema_validation_gaps(name, payload, schema_path))
    return {
        "ok": not gaps,
        "contracts": loaded,
        "required_gaps": gaps,
    }
