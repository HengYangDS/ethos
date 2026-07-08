"""Documentation command-example checks."""

from __future__ import annotations

import re
import shlex
from typing import TYPE_CHECKING

from ethos.repository.registry.commands import RETIRED_PUBLIC_ROOTS
from ethos.repository.registry.commands import known_commands
from ethos.repository.registry.commands import public_commands
from ethos.repository.registry.docs.health import OBSERVATIONAL_DOC_PREFIXES
from ethos.repository.registry.docs.links import markdown_paths

if TYPE_CHECKING:
    from pathlib import Path

ALLOWED_NON_ETHOS_ROOTS = ("git", "npm", "npx", "pip", "python", "uv")
REQUIRED_COMMAND_EXAMPLES = (
    "ethos land",
    "ethos publish",
    "ethos report",
)
ENV_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
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
    "ethos quality module-layout",
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
    "ethos lane retire-superseded",
    "ethos lane retire-unbound",
    "ethos parity",
    "ethos parity ledger",
    "ethos parity gaps",
    "ethos parity shadow",
}
GROUPED_COMMANDS = {
    "campaign",
    "intake",
    "quality",
    "assistants",
    "playbooks",
    "fleet",
    "lane",
    "parity",
}


def command_examples_report(root: Path) -> dict[str, object]:
    """Report command examples that reference retired or unknown command roots."""
    gaps: list[str] = []
    examples: list[dict[str, str]] = []
    for path in markdown_paths(root):
        relative_path = path.relative_to(root).as_posix()
        scope = command_scope(relative_path)
        enforce_public_plane = not relative_path.startswith(OBSERVATIONAL_DOC_PREFIXES)
        for lineno, logical_command in bash_logical_commands(path):
            command = command_root(logical_command)
            record = {
                "path": relative_path,
                "line": str(lineno),
                "command": logical_command,
                "root": command,
                "scope": scope,
                "normalized_command": " ".join(normalized_command_tokens(logical_command)),
            }
            examples.append(record)
            if not enforce_public_plane:
                continue
            if command in RETIRED_PUBLIC_ROOTS:
                gaps.append(f"retired_command_example:{record['path']}:{lineno}:{command}")
            elif command == "ethos" and not known_ethos_command(logical_command):
                gaps.append(
                    f"unknown_ethos_command_example:{record['path']}:{lineno}:"
                    f"{best_ethos_command_key(logical_command) or 'ethos'}"
                )
            elif command != "ethos" and command not in ALLOWED_NON_ETHOS_ROOTS:
                gaps.append(f"unknown_command_example:{record['path']}:{lineno}:{command}")
    if not gaps and requires_product_examples(examples):
        for required in REQUIRED_COMMAND_EXAMPLES:
            if not has_command_example(examples, required):
                gaps.append(f"missing_command_example:{required}")
    return {"ok": not gaps, "required_gaps": gaps, "examples": examples}


def command_root(command: str) -> str:
    """Return the executable root for a shell command example."""
    tokens = normalized_command_tokens(command)
    if not tokens:
        return ""
    if tokens[0] == "ethos":
        return "ethos"
    if tokens[0] == "env":
        tokens = tokens[1:]
    while tokens and ENV_ASSIGNMENT.match(tokens[0]):
        tokens = tokens[1:]
    return tokens[0] if tokens else ""


def command_scope(path: str) -> str:
    """Return command-example scope for a repository-relative docs path."""
    if path.startswith("evidence/"):
        return "evidence"
    if path.startswith("docs/archive/"):
        return "archive"
    return "product"


def tokens(command: str) -> list[str]:
    """Split a shell command example, falling back on whitespace for malformed quotes."""
    try:
        return shlex.split(command, comments=False, posix=True)
    except ValueError:
        return command.split()


def ethos_command_key(command: str) -> str:
    """Return the primary `ethos` command key for a command example."""
    command_tokens = normalized_command_tokens(command)
    if command_tokens[:1] != ["ethos"]:
        return ""
    if len(command_tokens) == 1:
        return "ethos"
    return " ".join(command_tokens[:2])


def known_ethos_command(command: str) -> bool:
    """Return whether an `ethos` command example is known."""
    command_tokens = normalized_command_tokens(command)
    if command_tokens[:1] != ["ethos"]:
        return False
    if len(command_tokens) >= 3 and command_tokens[1] in GROUPED_COMMANDS:
        return " ".join(command_tokens[:3]) in KNOWN_ETHOS_COMMANDS
    key = ethos_command_key(command)
    return bool(key) and (
        key in KNOWN_ETHOS_COMMANDS or key in known_commands() or key in public_commands()
    )


def has_command_example(examples: list[dict[str, str]], required: str) -> bool:
    """Return whether product docs examples include a required command prefix."""
    required_tokens = tokens(required)
    for example in examples:
        if example["scope"] != "product":
            continue
        normalized = normalized_command_tokens(example["command"])
        if normalized[: len(required_tokens)] == required_tokens:
            return True
    return False


def requires_product_examples(examples: list[dict[str, str]]) -> bool:
    """Return whether product-level examples are expected for the scanned docs set."""
    return has_command_example(examples, "ethos prove")


def bash_logical_commands(path: Path) -> list[tuple[int, str]]:
    """Return logical shell commands from bash/sh fenced blocks."""
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


def best_ethos_command_key(command: str) -> str:
    """Return the most specific ethos command key useful for diagnostics."""
    command_tokens = normalized_command_tokens(command)
    if command_tokens[:1] != ["ethos"]:
        return ""
    if len(command_tokens) >= 3 and command_tokens[1] in GROUPED_COMMANDS:
        return " ".join(command_tokens[:3])
    return ethos_command_key(command)


def normalized_command_tokens(command: str) -> list[str]:
    """Return command tokens normalized to the underlying ethos invocation when wrapped."""
    stripped = strip_command_environment(tokens(command))
    ethos_tokens = ethos_invocation_tokens(stripped)
    return ethos_tokens or stripped


def strip_command_environment(command_tokens: list[str]) -> list[str]:
    """Remove leading env and KEY=VALUE assignments from shell command tokens."""
    if command_tokens[:1] == ["env"]:
        command_tokens = command_tokens[1:]
    while command_tokens and ENV_ASSIGNMENT.match(command_tokens[0]):
        command_tokens = command_tokens[1:]
    return command_tokens


def ethos_invocation_tokens(command_tokens: list[str]) -> list[str]:
    """Return tokens from an underlying ethos invocation inside common wrappers."""
    if command_tokens[:1] == ["ethos"]:
        return command_tokens
    if command_tokens[:2] == ["uv", "run"] and "ethos" in command_tokens[2:]:
        command_indices = [
            index for index, token in enumerate(command_tokens[2:], start=2) if token == "ethos"
        ]
        return command_tokens[command_indices[-1] :]
    if len(command_tokens) >= 3 and command_tokens[1:3] == ["-m", "ethos.cli"]:
        return ["ethos", *command_tokens[3:]]
    return []
