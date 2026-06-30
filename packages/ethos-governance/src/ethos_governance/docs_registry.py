from __future__ import annotations

from pathlib import Path

REQUIRED_FIELDS = ("subject", "role", "state", "relations")


def _front_matter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    header = text.split("---", 2)[1]
    values: dict[str, str] = {}
    current_key = ""
    nested: list[str] = []
    for line in header.splitlines():
        if line.startswith((" ", "\t")) and current_key:
            nested.append(line.strip())
            continue
        if current_key and nested:
            values[current_key] = "; ".join(nested)
            nested = []
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        current_key = key.strip()
        values[current_key] = value.strip()
    if current_key and nested:
        values[current_key] = "; ".join(nested)
    return values


def build_docs_registry(root: Path) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for path in sorted((root / "docs").rglob("*.md")):
        metadata = _front_matter(path)
        relative = path.relative_to(root).as_posix()
        entries.append(
            {
                "path": relative,
                "subject": metadata.get("subject", ""),
                "role": metadata.get("role", ""),
                "state": metadata.get("state", ""),
                "relations": metadata.get("relations", ""),
            }
        )
    return entries


def docs_health_report(root: Path) -> dict[str, object]:
    registry = build_docs_registry(root)
    missing = [
        entry["path"]
        for entry in registry
        if any(not entry[field] for field in REQUIRED_FIELDS)
    ]
    return {
        "ok": not missing,
        "document_count": len(registry),
        "missing_metadata": missing,
        "registry": registry,
    }
