from __future__ import annotations

import fnmatch
import tomllib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

PUBLIC_WORKFLOW_COMMANDS = (
    "ethos status",
    "ethos plan",
    "ethos prove",
    "ethos land",
    "ethos publish",
)
READER_VIEW_COMMANDS = ("ethos orient",)
SCORECARD_COMMANDS = ("ethos report",)
SETUP_COMMANDS = (
    "ethos init",
    "ethos adopt",
    "ethos doctor",
)
MAINTAINER_REFERENCE_COMMANDS = (
    "ethos audit",
    "ethos openspec",
    "ethos campaign",
    "ethos intake",
    "ethos quality",
    "ethos assistants",
    "ethos playbooks",
    "ethos fleet",
    "ethos lane",
    "ethos hook",
    "ethos parity",
    "ethos explain",
    "ethos docs",
)
GOVERNANCE_GATE_COMMANDS = ("openspec validate --all --strict --json",)
LOCAL_CLOSEOUT_COMMANDS = ("ethos land --closeout --apply --authorize --expect-head <HEAD>",)
EVIDENCE_REFRESH_COMMANDS = (
    "ethos parity shadow --adopter <adopter-id> --target <repo> --execute --write-evidence",
)
PUBLIC_COMMANDS = (*PUBLIC_WORKFLOW_COMMANDS,)
KNOWN_COMMANDS = (
    *PUBLIC_WORKFLOW_COMMANDS,
    *READER_VIEW_COMMANDS,
    *SCORECARD_COMMANDS,
    *SETUP_COMMANDS,
    *MAINTAINER_REFERENCE_COMMANDS,
)

RETIRED_PUBLIC_ROOTS = (
    "wt",
    "proof",
    "mission",
    "skill-evolution",
    "agent-surface-contract",
)
RETIRED_PUBLIC_COMMAND_PREFIXES = (
    "ethos kernel",
    "ethos governance",
    "ethos workspace",
    "ethos agent",
    "ethos project",
    "ethos node",
)
DEFAULT_HISTORICAL_EXEMPT_ROOTS = ("evidence", "docs/archive")


def public_commands() -> tuple[str, ...]:
    return PUBLIC_COMMANDS


def known_commands() -> tuple[str, ...]:
    return KNOWN_COMMANDS


def _command_surface_policy(root: Path) -> dict[str, object]:
    path = root / "rules" / "ethos" / "command-surface.toml"
    if not path.exists():
        return {}
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return {}
    policy = payload.get("policy")
    return policy if isinstance(policy, dict) else {}


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _all_doc_paths(root: Path) -> tuple[Path, ...]:
    paths = [root / "README.md", root / "CONTRIBUTING.md", root / "CHANGELOG.md"]
    docs = root / "docs"
    if docs.exists():
        paths.extend(sorted(docs.rglob("*.md")))
    return tuple(path for path in paths if path.exists())


def _policy_doc_paths(root: Path) -> tuple[Path, ...]:
    policy = _command_surface_policy(root)
    paths = list(_all_doc_paths(root))
    current_docs = _string_list(policy.get("current_docs"))
    current_globs = _string_list(policy.get("current_doc_globs"))
    retired_reference_docs = set(_string_list(policy.get("retired_reference_docs")))
    historical_roots = tuple(
        _string_list(policy.get("historical_exempt_roots")) or DEFAULT_HISTORICAL_EXEMPT_ROOTS
    )
    if current_docs or current_globs:
        selected: list[Path] = []
        for path in paths:
            relative = path.relative_to(root).as_posix()
            if relative in retired_reference_docs:
                continue
            if relative in current_docs or any(
                fnmatch.fnmatchcase(relative, pattern) for pattern in current_globs
            ):
                selected.append(path)
        return tuple(selected)
    return tuple(
        path
        for path in paths
        if not _is_historical_path(path.relative_to(root).as_posix(), historical_roots)
    )


def _is_historical_path(relative: str, historical_roots: tuple[str, ...]) -> bool:
    return any(
        relative == root or relative.startswith(f"{root.rstrip('/')}/") for root in historical_roots
    )


def _scan_retired_public_roots(root: Path) -> list[str]:
    mentions: list[str] = []
    for path in _policy_doc_paths(root):
        relative = path.relative_to(root).as_posix()
        in_fence = False
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("```"):
                in_fence = stripped in {"```bash", "```sh"} if not in_fence else False
                continue
            if not stripped:
                continue
            if in_fence:
                command_root = stripped.split()[0]
                if command_root in RETIRED_PUBLIC_ROOTS:
                    mentions.append(f"{relative}:{lineno}:{command_root}")
            for retired in RETIRED_PUBLIC_ROOTS:
                if f"`{retired}`" in stripped:
                    mentions.append(f"{relative}:{lineno}:{retired}")
    return mentions


def _scan_retired_public_command_prefixes(root: Path) -> list[str]:
    mentions: list[str] = []
    for path in _policy_doc_paths(root):
        relative = path.relative_to(root).as_posix()
        in_fence = False
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("```"):
                in_fence = stripped in {"```bash", "```sh"} if not in_fence else False
                continue
            if not stripped:
                continue
            if in_fence:
                tokens = stripped.split()
                if len(tokens) >= 2:
                    command_prefix = " ".join(tokens[:2])
                    if command_prefix in RETIRED_PUBLIC_COMMAND_PREFIXES:
                        mentions.append(f"{relative}:{lineno}:{command_prefix}")
            for retired in RETIRED_PUBLIC_COMMAND_PREFIXES:
                if f"`{retired}`" in stripped:
                    mentions.append(f"{relative}:{lineno}:{retired}")
    return mentions


def command_registry_report(root: Path | None = None) -> dict[str, object]:
    classified = (
        set(PUBLIC_WORKFLOW_COMMANDS)
        | set(READER_VIEW_COMMANDS)
        | set(SCORECARD_COMMANDS)
        | set(SETUP_COMMANDS)
        | set(MAINTAINER_REFERENCE_COMMANDS)
    )
    advanced_public_commands = [command for command in PUBLIC_COMMANDS if command not in classified]
    leaked = [
        command for command in PUBLIC_COMMANDS if command.split(" ", 1)[0] in RETIRED_PUBLIC_ROOTS
    ]
    mentions = _scan_retired_public_roots(root) if root else []
    retired_prefix_mentions = _scan_retired_public_command_prefixes(root) if root else []
    required_gaps = (
        [f"retired_public_root:{command}" for command in leaked]
        + [f"advanced_public_command:{command}" for command in advanced_public_commands]
        + [f"retired_public_root_mention:{mention}" for mention in mentions]
        + [
            f"retired_public_command_prefix_mention:{mention}"
            for mention in retired_prefix_mentions
        ]
    )
    return {
        "ok": not required_gaps,
        "public_commands": list(PUBLIC_COMMANDS),
        "known_commands": list(KNOWN_COMMANDS),
        "public_workflow_commands": list(PUBLIC_WORKFLOW_COMMANDS),
        "reader_view_commands": list(READER_VIEW_COMMANDS),
        "scorecard_commands": list(SCORECARD_COMMANDS),
        "setup_commands": list(SETUP_COMMANDS),
        "maintainer_reference_commands": list(MAINTAINER_REFERENCE_COMMANDS),
        "governance_gate_commands": list(GOVERNANCE_GATE_COMMANDS),
        "local_closeout_commands": list(LOCAL_CLOSEOUT_COMMANDS),
        "evidence_refresh_commands": list(EVIDENCE_REFRESH_COMMANDS),
        "advanced_public_commands": advanced_public_commands,
        "public_workflow_count": len(PUBLIC_WORKFLOW_COMMANDS),
        "reader_view_count": len(READER_VIEW_COMMANDS),
        "scorecard_count": len(SCORECARD_COMMANDS),
        "setup_count": len(SETUP_COMMANDS),
        "known_command_count": len(KNOWN_COMMANDS),
        "maintainer_reference_count": len(MAINTAINER_REFERENCE_COMMANDS),
        "retired_public_roots": leaked,
        "retired_public_root_mentions": mentions,
        "retired_public_command_prefix_mentions": retired_prefix_mentions,
        "required_gaps": required_gaps,
        "retired_roots_policy": list(RETIRED_PUBLIC_ROOTS),
        "retired_command_prefix_policy": list(RETIRED_PUBLIC_COMMAND_PREFIXES),
    }
