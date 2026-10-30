"""Authored files of the signed adopted-repository fixture."""

from __future__ import annotations

# The adopted repository's authored files, written as LF bytes on every host.
SMOKE_CHANGE = "openspec/changes/smoke-change"
ADOPTER_FILES = {
    ".ethos/profile.toml": (
        'profile_id = "installed-cli-adopter"\n\n[openspec]\nmaterial_paths = ["**"]\n'
    ),
    ".ethos/release.toml": """[publication]
local_verification_command = "git fsck --no-reflogs"
local_installation_command = "git --version"

[[publication.peers]]
id = "file"
provider = "git"
role = "package_smoke"
git_remote = "file"
capabilities = ["repository", "publication"]
""",
    ".gitattributes": "* text=auto eol=lf\nline-ending-*.txt -text\n",
    f"{SMOKE_CHANGE}/.openspec.yaml": "schema: spec-driven\n",
    f"{SMOKE_CHANGE}/proposal.md": (
        "## Why\n\nExercise the installed package lifecycle.\n\n"
        "## What Changes\n\n- Add one package-smoke change.\n\n"
        "## Capabilities\n\n### New Capabilities\n\n"
        "- `package-smoke`: installed governance of one official Change.\n\n"
        "### Modified Capabilities\n\n- None.\n\n"
        "## Impact\n\n- Disposable package-smoke fixture.\n\n"
        "## Out of Scope\n\n- Product behavior.\n"
    ),
    f"{SMOKE_CHANGE}/design.md": (
        "## Context\n\nPackage-only lifecycle proof.\n\n"
        "## Goals / Non-Goals\n\nGovern one Change without product behavior.\n\n"
        "## Decisions\n\nUse only official OpenSpec artifacts.\n\n"
        "## Risks / Trade-offs\n\nNone beyond the disposable fixture.\n"
    ),
    f"{SMOKE_CHANGE}/tasks.md": "## 1. Package smoke\n\n- [x] 1.1 Exercise installed lifecycle.\n",
    f"{SMOKE_CHANGE}/specs/package-smoke/spec.md": (
        "## Purpose\n\n"
        "Verify installed governance of native repository changes without source access.\n\n"
        "## ADDED Requirements\n\n"
        "### Requirement: Installed lifecycle\n\n"
        "The installed package SHALL govern an official OpenSpec Change.\n\n"
        "#### Scenario: Package smoke runs\n\n"
        "- **WHEN** the installed lifecycle executes\n"
        "- **THEN** no parallel intent carrier is required\n"
    ),
    "README.md": "# installed CLI adopter\n",
    "AGENTS.md": "# Agents\n",
    ".editorconfig": (
        "root = true\n\n[*]\ncharset = utf-8\nend_of_line = lf\ninsert_final_newline = true\n"
    ),
    ".config/checks/prettier/prettier.toml": 'printWidth = 100\nproseWrap = "preserve"\n',
    ".config/checks/taplo/taplo.toml": "[formatting]\ncolumn_width = 100\n",
    ".config/mise/config.toml": (
        '[settings]\nlocked = true\n\n[tasks]\nbootstrap = "git --version"\n'
        'check = "git fsck --no-reflogs"\nfix = "git add --renormalize ."\n'
    ),
    ".config/mise/mise.lock": "",
}
