from __future__ import annotations

from pathlib import Path

from ethos_governance.command_registry import RETIRED_PUBLIC_ROOTS

REQUIRED_FIELDS = ("subject", "role", "state", "relations")
ALLOWED_NON_ETHOS_ROOTS = ("git", "pip", "python", "uv")


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


def _markdown_paths(root: Path) -> tuple[Path, ...]:
    paths = [root / "README.md", root / "CONTRIBUTING.md", root / "CHANGELOG.md"]
    paths.extend(sorted((root / "docs").rglob("*.md")))
    return tuple(path for path in paths if path.exists())


def command_examples_report(root: Path) -> dict[str, object]:
    gaps: list[str] = []
    examples: list[dict[str, str]] = []
    for path in _markdown_paths(root):
        in_bash = False
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("```"):
                in_bash = stripped in {"```bash", "```sh"} if not in_bash else False
                continue
            if not in_bash or not stripped or stripped.startswith("#"):
                continue
            command = stripped.split()[0]
            record = {
                "path": path.relative_to(root).as_posix(),
                "line": str(lineno),
                "command": stripped,
            }
            examples.append(record)
            if command in RETIRED_PUBLIC_ROOTS:
                gaps.append(f"retired_command_example:{record['path']}:{lineno}:{command}")
            elif command != "ethos" and command not in ALLOWED_NON_ETHOS_ROOTS:
                gaps.append(f"unknown_command_example:{record['path']}:{lineno}:{command}")
    return {"ok": not gaps, "required_gaps": gaps, "examples": examples}
