"""System-contract loader — makes system/*.toml load-bearing.

Reads the machine governance kernel's declarative contracts off disk so downstream
code derives behavior from the contract instead of hardcoding it. This loader
lives in ethos-contracts, the layer permitted TOML IO; the kernel stays a pure
leaf, so the contract-name list is owned here.
"""

from __future__ import annotations

import json
import tomllib
from typing import TYPE_CHECKING

import jsonschema

from ethos.contracts.verdict import close_verdict

if TYPE_CHECKING:
    from pathlib import Path

SYSTEM_CONTRACTS = (
    "formats",
    "routing",
    "surfaces",
    "tools",
    "evidence_boundaries",
)

_IDENTITY_FIELDS = {
    "surfaces": ("surface", "name", "surface"),
    "tools": ("tool", "concern", "tool"),
}


def load_system_contract(root: Path, name: str) -> dict[str, object]:
    """Load one root-owned ``system/<name>.toml`` contract or fail closed."""
    path = root / "system" / f"{name}.toml"
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
    declaration_issues: list[dict[str, object]] = []
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
        declaration_issues.extend(_declaration_identity_issues(name, payload))
        schema_ref = payload.get("schema")
        if isinstance(schema_ref, str) and schema_ref:
            schema_path = root / schema_ref
            if not schema_path.exists():
                gaps.append(f"system_schema_ref_missing:{name}:{schema_ref}")
            else:
                gaps.extend(schema_validation_gaps(name, payload, schema_path))
    declaration_issues.sort(
        key=lambda item: (str(item["category"]), str(item["kind"]), str(item["identity"]))
    )
    gaps.extend(_declaration_gap(issue) for issue in declaration_issues)
    return {
        "verdict": close_verdict("pass", required_gaps=tuple(gaps)),
        "contracts": loaded,
        "declaration_issues": declaration_issues,
        "required_gaps": gaps,
    }


def _declaration_identity_issues(name: str, payload: dict[str, object]) -> list[dict[str, object]]:
    descriptor = _IDENTITY_FIELDS.get(name)
    if descriptor is None:
        return []
    array, identity_field, kind = descriptor
    entries = payload.get(array)
    if not isinstance(entries, list):
        return []
    groups: dict[str, list[dict[str, object]]] = {}
    for entry in entries:
        if isinstance(entry, dict) and isinstance(identity := entry.get(identity_field), str):
            groups.setdefault(identity, []).append(entry)
    return [
        {
            "category": "duplicate"
            if all(item == declarations[0] for item in declarations)
            else "conflict",
            "relation": "owner",
            "kind": kind,
            "identity": identity,
            "sources": [f"system/{name}.toml"],
        }
        for identity, declarations in groups.items()
        if len(declarations) > 1
    ]


def _declaration_gap(issue: dict[str, object]) -> str:
    sources = issue.get("sources")
    source_text = ",".join(str(source) for source in sources) if isinstance(sources, list) else ""
    return (
        f"semantic_{issue['relation']}_{issue['category']}:{issue['kind']}:"
        f"{issue['identity']}:{source_text}"
    )
