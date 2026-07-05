from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEXT_SUFFIXES = {
    "",
    ".cfg",
    ".css",
    ".ini",
    ".json",
    ".lock",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
FORBIDDEN_VENDOR_SURFACES = tuple(
    token.lower()
    for token in (
        "Git" + "Nexus",
        "git" + "nexus",
        "codebase" + "-" + "memory",
        "." + "git" + "nexus",
    )
)


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [ROOT / line for line in result.stdout.splitlines() if line]


def is_text_candidate(path: Path) -> bool:
    if path.suffix.lower() in TEXT_SUFFIXES:
        return True
    return path.name in {"AGENTS.md", "README", "LICENSE"}


def test_repository_truth_has_no_unapproved_vendor_memory_surface() -> None:
    findings: list[str] = []
    for path in tracked_files():
        if not is_text_candidate(path):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for surface in FORBIDDEN_VENDOR_SURFACES:
            if surface in text:
                findings.append(f"{path.relative_to(ROOT).as_posix()}: {surface}")

    assert findings == []
