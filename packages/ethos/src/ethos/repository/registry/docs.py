from __future__ import annotations

import re
import shlex
import tomllib
from typing import TYPE_CHECKING
from urllib.parse import unquote

from ethos.repository.registry.commands import RETIRED_PUBLIC_ROOTS
from ethos.repository.registry.commands import known_commands
from ethos.repository.registry.commands import public_commands

if TYPE_CHECKING:
    from pathlib import Path

REQUIRED_FIELDS = ("subject", "role", "state", "relations")
ALLOWED_NON_ETHOS_ROOTS = ("git", "npm", "npx", "pip", "python", "uv")
OBSERVATIONAL_DOC_PREFIXES = ("evidence/", "docs/archive/")
REQUIRED_COMMAND_EXAMPLES = (
    "ethos land",
    "ethos publish",
    "ethos report",
)
VISIBLE_SECTION_LABELS = ("Status:", "Purpose:", "See also:")
DEFAULT_ALLOWED_STATES = {
    "active",
    "archived",
    "canonical",
    "experimental",
    "planned",
    "superseded",
}
_ENV_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
GLOSSARY_TERMS = (
    "Command Plane",
    "Authority",
    "Subject",
    "Commitment",
    "Change",
    "Evidence",
    "Claim",
    "Chronicle",
)


KNOWN_ETHOS_COMMANDS = {
    "ethos status",
    "ethos plan",
    "ethos prove",
    "ethos land",
    "ethos publish",
    "ethos init",
    "ethos adopt",
    "ethos doctor",
    "ethos report",
    "ethos explain",
    "ethos docs",
    "ethos campaign",
    "ethos campaign status",
    "ethos campaign hypotheses",
    "ethos campaign closeout",
    "ethos intake",
    "ethos intake status",
    "ethos audit",
    "ethos openspec",
    "ethos quality",
    "ethos quality asset-policy",
    "ethos quality command-surface",
    "ethos quality format-policy",
    "ethos quality projection-drift",
    "ethos quality standards",
    "ethos quality package-ontology",
    "ethos quality schemas",
    "ethos quality gates",
    "ethos quality generated-artifacts",
    "ethos quality docs",
    "ethos quality docs-topology",
    "ethos quality markdown-links",
    "ethos quality shell",
    "ethos quality toml",
    "ethos quality yaml",
    "ethos quality code-size",
    "ethos quality npm",
    "ethos quality proof-policy",
    "ethos quality tool-profiles",
    "ethos quality coupling-audit",
    "ethos quality commits",
    "ethos quality release",
    "ethos quality release-policy",
    "ethos quality sbom",
    "ethos quality release-attestation",
    "ethos quality command-registry",
    "ethos quality evidence-freshness",
    "ethos quality claims",
    "ethos quality docs-registry",
    "ethos quality command-examples",
    "ethos quality provenance",
    "ethos assistants",
    "ethos assistants doctor",
    "ethos assistants check-projections",
    "ethos assistants mcp-manifest",
    "ethos assistants mcp-server",
    "ethos assistants context",
    "ethos assistants search",
    "ethos assistants context-index",
    "ethos assistants context-purge",
    "ethos assistants context-eval",
    "ethos playbooks",
    "ethos playbooks route",
    "ethos playbooks check",
    "ethos fleet",
    "ethos fleet inspect",
    "ethos fleet retirement-readiness",
    "ethos lane",
    "ethos lane status",
    "ethos lane candidate",
    "ethos lane start",
    "ethos lane prewrite",
    "ethos lane refresh-base",
    "ethos lane bind-claim",
    "ethos lane hydrate",
    "ethos lane retire-landed",
    "ethos lane retire-unbound",
    "ethos parity",
    "ethos parity ledger",
    "ethos parity gaps",
    "ethos parity shadow",
}


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


def _taxonomy(root: Path) -> dict[str, object]:
    path = root / "docs" / "_meta" / "taxonomy.toml"
    if not path.exists():
        return {}
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return {}


def _allowed_states(root: Path) -> set[str]:
    taxonomy = _taxonomy(root)
    states = taxonomy.get("states") if isinstance(taxonomy, dict) else {}
    allowed = states.get("allowed") if isinstance(states, dict) else []
    configured = {str(item) for item in allowed if isinstance(item, str)}
    return configured or set(DEFAULT_ALLOWED_STATES)


def docs_health_report(root: Path) -> dict[str, object]:
    registry = build_docs_registry(root)
    missing = [
        entry["path"] for entry in registry if any(not entry[field] for field in REQUIRED_FIELDS)
    ]
    allowed_states = _allowed_states(root)
    invalid_state = [
        f"invalid_state:{entry['path']}:{entry['state']}"
        for entry in registry
        if allowed_states and entry["state"] and entry["state"] not in allowed_states
    ]
    subject_paths: dict[str, list[str]] = {}
    for entry in registry:
        if entry["subject"]:
            subject_paths.setdefault(entry["subject"], []).append(entry["path"])
    duplicate_subjects = [
        f"duplicate_subject:{subject}:{','.join(paths)}"
        for subject, paths in sorted(subject_paths.items())
        if len(paths) > 1
    ]
    visible_section_gaps = _visible_section_gaps(root, registry)
    required_gaps = missing + invalid_state + duplicate_subjects + visible_section_gaps
    return {
        "ok": not required_gaps,
        "document_count": len(registry),
        "missing_metadata": missing,
        "invalid_state": invalid_state,
        "duplicate_subjects": duplicate_subjects,
        "missing_visible_sections": visible_section_gaps,
        "required_gaps": required_gaps,
        "registry": registry,
    }


def _visible_section_gaps(root: Path, registry: list[dict[str, str]]) -> list[str]:
    gaps: list[str] = []
    for entry in registry:
        if not _requires_visible_sections(entry):
            continue
        path = root / entry["path"]
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for label in VISIBLE_SECTION_LABELS:
            if label not in text:
                gaps.append(f"missing_visible_section:{entry['path']}:{label[:-1].lower()}")
    return gaps


def _requires_visible_sections(entry: dict[str, str]) -> bool:
    if entry["path"].startswith(OBSERVATIONAL_DOC_PREFIXES):
        return False
    return entry["state"] in {"canonical", "active"}


def docs_quality_report(root: Path) -> dict[str, object]:
    health = docs_health_report(root)
    link_integrity = _link_integrity_report(root)
    glossary = _glossary_report(root)
    checks = {
        "taxonomy": {
            "ok": not health["invalid_state"] and not health["duplicate_subjects"],
            "required_gaps": list(health["invalid_state"]) + list(health["duplicate_subjects"]),
        },
        "visible_structure": {
            "ok": not health["missing_visible_sections"],
            "required_gaps": list(health["missing_visible_sections"]),
        },
        "stable_paths": _stable_paths_report(root),
        "link_integrity": link_integrity,
        "glossary": glossary,
    }
    command_examples = command_examples_report(root)
    required_gaps = [gap for check in checks.values() for gap in check["required_gaps"]] + list(
        command_examples["required_gaps"]
    )
    return {
        "ok": not required_gaps and health["ok"] and command_examples["ok"],
        "style_goals": ["faithful", "expressive", "elegant"],
        "required_gaps": required_gaps,
        "checks": checks,
        "health": health,
        "command_examples": command_examples,
    }


def _link_integrity_report(root: Path) -> dict[str, object]:
    gaps: list[str] = []
    for path in _markdown_paths(root):
        relative = path.relative_to(root).as_posix()
        if relative.startswith("evidence/"):
            continue
        for lineno, target in _markdown_links(path):
            path_part, _, fragment = target.partition("#")
            if not path_part and fragment:
                target_path = path
            elif _is_external_link(path_part):
                continue
            else:
                target_path = (path.parent / unquote(path_part)).resolve()
            if not target_path.exists():
                gaps.append(f"broken_link:{relative}:{lineno}:{target}")
                continue
            if fragment and target_path.suffix == ".md":
                anchors = _markdown_anchors(target_path)
                if fragment not in anchors:
                    gaps.append(f"broken_anchor:{relative}:{lineno}:{target}")
    return {"ok": not gaps, "required_gaps": gaps}


def _markdown_links(path: Path) -> list[tuple[int, str]]:
    links: list[tuple[int, str]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        for match in _MARKDOWN_LINK.finditer(line):
            target = match.group(1).strip()
            if not target or target.startswith("<"):
                continue
            target = target.split(None, 1)[0]
            links.append((lineno, target))
    return links


def _is_external_link(target: str) -> bool:
    return "://" in target or target.startswith(("mailto:", "tel:"))


def _markdown_anchors(path: Path) -> set[str]:
    anchors: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        match = _HEADING.match(line)
        if not match:
            continue
        anchors.add(_slugify_heading(match.group(2)))
    return anchors


def _slugify_heading(text: str) -> str:
    text = re.sub(r"`([^`]+)`", r"\1", text.strip().lower())
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff _-]", "", text)
    return re.sub(r"[\s_]+", "-", text).strip("-")


def _glossary_report(root: Path) -> dict[str, object]:
    path = root / "docs" / "reference" / "glossary.md"
    if not path.exists():
        return {"ok": False, "required_gaps": ["glossary_missing:docs/reference/glossary.md"]}
    text = path.read_text(encoding="utf-8")
    gaps = [f"glossary_term_missing:{term}" for term in GLOSSARY_TERMS if f"## {term}" not in text]
    return {"ok": not gaps, "required_gaps": gaps}


def _stable_paths_report(root: Path) -> dict[str, object]:
    required = {
        "docs/index.md",
        "docs/start/quickstart.md",
        "docs/reference/command-plane.md",
        "docs/governance/docs-registry.md",
        "docs/reference/glossary.md",
    }
    path = root / "docs" / "_meta" / "stable_paths.toml"
    configured: set[str] = set()
    if path.exists():
        try:
            payload = tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError:
            return {"ok": False, "required_gaps": ["stable_paths_invalid_toml"]}
        configured = {
            str(item.get("path"))
            for item in payload.get("stable_path", [])
            if isinstance(item, dict) and item.get("path")
        }
    missing = sorted(f"stable_path_missing:{item}" for item in required if item not in configured)
    missing.extend(
        f"stable_path_target_missing:{item}"
        for item in sorted(configured)
        if not (root / item).exists()
    )
    return {"ok": not missing, "required_gaps": missing, "configured": sorted(configured)}


def _markdown_paths(root: Path) -> tuple[Path, ...]:
    paths = [root / "README.md", root / "CONTRIBUTING.md", root / "CHANGELOG.md"]
    paths.extend(sorted((root / "docs").rglob("*.md")))
    paths.extend(sorted((root / "evidence").rglob("*.md")))
    return tuple(path for path in paths if path.exists())


def _command_root(command: str) -> str:
    tokens = _normalized_command_tokens(command)
    if not tokens:
        return ""
    if tokens[0] == "ethos":
        return "ethos"
    if tokens[0] == "env":
        tokens = tokens[1:]
    while tokens and _ENV_ASSIGNMENT.match(tokens[0]):
        tokens = tokens[1:]
    return tokens[0] if tokens else ""


def _command_scope(path: str) -> str:
    if path.startswith("evidence/"):
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
    tokens = _normalized_command_tokens(command)
    if tokens[:1] != ["ethos"]:
        return ""
    if len(tokens) == 1:
        return "ethos"
    return " ".join(tokens[:2])


def _known_ethos_command(command: str) -> bool:
    tokens = _normalized_command_tokens(command)
    if tokens[:1] != ["ethos"]:
        return False
    grouped = {
        "campaign",
        "intake",
        "quality",
        "assistants",
        "playbooks",
        "fleet",
        "lane",
        "parity",
    }
    if len(tokens) >= 3 and tokens[1] in grouped:
        return " ".join(tokens[:3]) in KNOWN_ETHOS_COMMANDS
    key = _ethos_command_key(command)
    return bool(key) and (
        key in KNOWN_ETHOS_COMMANDS or key in known_commands() or key in public_commands()
    )


def _has_command_example(examples: list[dict[str, str]], required: str) -> bool:
    required_tokens = _tokens(required)
    for example in examples:
        if example["scope"] != "current":
            continue
        normalized = _normalized_command_tokens(example["command"])
        if normalized[: len(required_tokens)] == required_tokens:
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
        for lineno, logical_command in _bash_logical_commands(path):
            command = _command_root(logical_command)
            record = {
                "path": relative_path,
                "line": str(lineno),
                "command": logical_command,
                "root": command,
                "scope": scope,
                "normalized_command": " ".join(_normalized_command_tokens(logical_command)),
            }
            examples.append(record)
            if not enforce_public_plane:
                continue
            if command in RETIRED_PUBLIC_ROOTS:
                gaps.append(f"retired_command_example:{record['path']}:{lineno}:{command}")
            elif command == "ethos" and not _known_ethos_command(logical_command):
                gaps.append(
                    f"unknown_ethos_command_example:{record['path']}:{lineno}:"
                    f"{_best_ethos_command_key(logical_command) or 'ethos'}"
                )
            elif command != "ethos" and command not in ALLOWED_NON_ETHOS_ROOTS:
                gaps.append(f"unknown_command_example:{record['path']}:{lineno}:{command}")
    if not gaps and _requires_product_examples(examples):
        for required in REQUIRED_COMMAND_EXAMPLES:
            if not _has_command_example(examples, required):
                gaps.append(f"missing_command_example:{required}")
    return {"ok": not gaps, "required_gaps": gaps, "examples": examples}


def _bash_logical_commands(path: Path) -> list[tuple[int, str]]:
    commands: list[tuple[int, str]] = []
    in_bash = False
    buffer: list[str] = []
    start_lineno = 0
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_bash and buffer:
                commands.append((start_lineno, " ".join(buffer).strip()))
                buffer = []
                start_lineno = 0
            in_bash = stripped in {"```bash", "```sh"} if not in_bash else False
            continue
        if not in_bash or not stripped or stripped.startswith("#"):
            continue
        continued = stripped.endswith("\\")
        part = stripped[:-1].rstrip() if continued else stripped
        if not buffer:
            start_lineno = lineno
        buffer.append(part)
        if continued:
            continue
        commands.append((start_lineno, " ".join(buffer).strip()))
        buffer = []
        start_lineno = 0
    if in_bash and buffer:
        commands.append((start_lineno, " ".join(buffer).strip()))
    return commands


def _best_ethos_command_key(command: str) -> str:
    tokens = _normalized_command_tokens(command)
    if tokens[:1] != ["ethos"]:
        return ""
    grouped = {
        "campaign",
        "intake",
        "quality",
        "assistants",
        "playbooks",
        "fleet",
        "lane",
        "parity",
    }
    if len(tokens) >= 3 and tokens[1] in grouped:
        return " ".join(tokens[:3])
    return _ethos_command_key(command)


def _normalized_command_tokens(command: str) -> list[str]:
    tokens = _strip_command_environment(_tokens(command))
    ethos_tokens = _ethos_invocation_tokens(tokens)
    return ethos_tokens or tokens


def _strip_command_environment(tokens: list[str]) -> list[str]:
    if tokens[:1] == ["env"]:
        tokens = tokens[1:]
    while tokens and _ENV_ASSIGNMENT.match(tokens[0]):
        tokens = tokens[1:]
    return tokens


def _ethos_invocation_tokens(tokens: list[str]) -> list[str]:
    if tokens[:1] == ["ethos"]:
        return tokens
    if tokens[:2] == ["uv", "run"] and "ethos" in tokens[2:]:
        command_indices = [
            index for index, token in enumerate(tokens[2:], start=2) if token == "ethos"
        ]
        return tokens[command_indices[-1] :]
    if len(tokens) >= 3 and tokens[1:3] == ["-m", "ethos.cli"]:
        return ["ethos", *tokens[3:]]
    return []
