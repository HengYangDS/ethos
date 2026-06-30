from __future__ import annotations

from pathlib import Path

PUBLIC_COMMANDS = (
    "ethos status",
    "ethos plan",
    "ethos prove",
    "ethos land",
    "ethos publish",
    "ethos init",
    "ethos adopt",
    "ethos doctor",
    "ethos campaign",
    "ethos intake",
    "ethos self",
    "ethos quality",
    "ethos assistants",
    "ethos playbooks",
    "ethos fleet",
    "ethos lane",
    "ethos parity",
    "ethos report",
    "ethos explain",
    "ethos docs",
)

RETIRED_PUBLIC_ROOTS = (
    "wt",
    "proof",
    "mission",
    "skill-evolution",
    "agent-surface-contract",
)


def public_commands() -> tuple[str, ...]:
    return PUBLIC_COMMANDS


def _doc_paths(root: Path) -> tuple[Path, ...]:
    paths = [root / "README.md", root / "CONTRIBUTING.md", root / "CHANGELOG.md"]
    docs = root / "docs"
    if docs.exists():
        paths.extend(sorted(docs.rglob("*.md")))
    return tuple(path for path in paths if path.exists())


def _scan_retired_public_roots(root: Path) -> list[str]:
    mentions: list[str] = []
    for path in _doc_paths(root):
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


def command_registry_report(root: Path | None = None) -> dict[str, object]:
    leaked = [
        command
        for command in PUBLIC_COMMANDS
        if command.split(" ", 1)[0] in RETIRED_PUBLIC_ROOTS
    ]
    mentions = _scan_retired_public_roots(root) if root else []
    required_gaps = [
        f"retired_public_root:{command}"
        for command in leaked
    ] + [
        f"retired_public_root_mention:{mention}"
        for mention in mentions
    ]
    return {
        "ok": not required_gaps,
        "public_commands": list(PUBLIC_COMMANDS),
        "retired_public_roots": leaked,
        "retired_public_root_mentions": mentions,
        "required_gaps": required_gaps,
        "retired_roots_policy": list(RETIRED_PUBLIC_ROOTS),
    }
