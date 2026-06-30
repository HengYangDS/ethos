from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError


def _repo_root() -> Path:
    return Path.cwd()


def _schema_dir(root: Path) -> Path:
    return root / "schemas" / "ethos"


def load_schema(name: str, *, root: Path | None = None) -> dict[str, Any]:
    base = _schema_dir(root or _repo_root())
    return json.loads((base / name).read_text(encoding="utf-8"))


def schema_validation_report(root: Path | None = None) -> dict[str, object]:
    repo = root or _repo_root()
    gaps: list[str] = []
    schemas: dict[str, dict[str, object]] = {}
    for path in sorted(_schema_dir(repo).glob("*.schema.json")):
        try:
            schema = json.loads(path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
        except (json.JSONDecodeError, SchemaError) as exc:
            gaps.append(f"{path.name}:{exc.__class__.__name__}")
            schemas[path.name] = {"ok": False, "error": str(exc)}
        else:
            schemas[path.name] = {"ok": True, "title": schema.get("title", "")}
    return {
        "ok": not gaps,
        "schema_count": len(schemas),
        "required_gaps": gaps,
        "schemas": schemas,
    }


def validate_ethos_result(
    payload: dict[str, Any],
    *,
    root: Path | None = None,
) -> dict[str, object]:
    schema = load_schema("result.schema.json", root=root)
    validator = Draft202012Validator(schema)
    try:
        validator.validate(payload)
    except ValidationError as exc:
        return {"ok": False, "required_gaps": [exc.message]}
    return {"ok": True, "required_gaps": []}
