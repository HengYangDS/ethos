from __future__ import annotations

import re
import shlex
from pathlib import Path

from ethos_repository.command_registry import RETIRED_PUBLIC_ROOTS, known_commands

REQUIRED_FIELDS = ("subject", "role", "state", "relations")
ALLOWED_NON_ETHOS_ROOTS = ("git", "npm", "npx", "pip", "python", "uv")
OBSERVATIONAL_DOC_PREFIXES = ("docs/evidence/", "docs/archive/")
REQUIRED_COMMAND_EXAMPLES = (
    "ethos land",
    "ethos publish",
    "ethos report",
)
_ENV_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


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
    doc_paths = list((root / "docs").rglob("*.md"))
    doc_paths.extend((root / "distributions").glob("*/README.md"))
    for path in sorted(doc_paths):
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


def _command_root(command: str) -> str:
    try:
        tokens = shlex.split(command, comments=False, posix=True)
    except ValueError:
        tokens = command.split()
    if not tokens:
        return ""
    if tokens[0] == "env":
        tokens = tokens[1:]
    while tokens and _ENV_ASSIGNMENT.match(tokens[0]):
        tokens = tokens[1:]
    return tokens[0] if tokens else ""


def _command_scope(path: str) -> str:
    if path.startswith("docs/evidence/"):
        return "evidence"
    if path.startswith("docs/archive/"):
        return "archive"
    return "current"


def _tokens(command: str) -> list[str]:
    try:
        return shlex.split(command, comments=False, posix=True)
    except ValueError:
        return command.split()


def _ethos_command_key(command: str) -> str:
    tokens = _tokens(command)
    if tokens[:1] != ["ethos"]:
        return ""
    if len(tokens) == 1:
        return "ethos"
    return " ".join(tokens[:2])


def _known_ethos_command(command: str) -> bool:
    key = _ethos_command_key(command)
    return bool(key) and key in known_commands()


def _has_command_example(examples: list[dict[str, str]], required: str) -> bool:
    required_tokens = _tokens(required)
    for example in examples:
        if example["scope"] != "current":
            continue
        if _tokens(example["command"])[: len(required_tokens)] == required_tokens:
            return True
    return False


def _requires_product_examples(examples: list[dict[str, str]]) -> bool:
    return _has_command_example(examples, "ethos prove")


def command_examples_report(root: Path) -> dict[str, object]:
    gaps: list[str] = []
    examples: list[dict[str, str]] = []
    for path in _markdown_paths(root):
        relative_path = path.relative_to(root).as_posix()
        scope = _command_scope(relative_path)
        enforce_public_plane = not relative_path.startswith(OBSERVATIONAL_DOC_PREFIXES)
        in_bash = False
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("```"):
                in_bash = stripped in {"```bash", "```sh"} if not in_bash else False
                continue
            if not in_bash or not stripped or stripped.startswith("#"):
                continue
            command = _command_root(stripped)
            record = {
                "path": relative_path,
                "line": str(lineno),
                "command": stripped,
                "root": command,
                "scope": scope,
            }
            examples.append(record)
            if not enforce_public_plane:
                continue
            if command in RETIRED_PUBLIC_ROOTS:
                gaps.append(f"retired_command_example:{record['path']}:{lineno}:{command}")
            elif command == "ethos" and not _known_ethos_command(stripped):
                gaps.append(
                    f"unknown_ethos_command_example:{record['path']}:{lineno}:"
                    f"{_ethos_command_key(stripped) or 'ethos'}"
                )
            elif command != "ethos" and command not in ALLOWED_NON_ETHOS_ROOTS:
                gaps.append(f"unknown_command_example:{record['path']}:{lineno}:{command}")
    if not gaps and _requires_product_examples(examples):
        for required in REQUIRED_COMMAND_EXAMPLES:
            if not _has_command_example(examples, required):
                gaps.append(f"missing_command_example:{required}")
    return {"ok": not gaps, "required_gaps": gaps, "examples": examples}
