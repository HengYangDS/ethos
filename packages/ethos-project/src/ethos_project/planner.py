from __future__ import annotations

import json
from pathlib import Path

PROFILES = ("generic", "python-package", "monorepo", "github", "gitlab")
OPENSPEC_FAMILIES = (
    "ethos-kernel",
    "ethos-project",
    "ethos-governance",
    "ethos-workspace",
    "ethos-agent",
    "ethos-distribution",
)
BASE_ADOPTION_FILES = (
    ".ethos/project.toml",
    ".ethos/workspace.toml",
    ".ethos/rules.toml",
    ".ethos/assistants.toml",
    ".ethos/release.toml",
    ".ethos/state/.gitignore",
    ".agents/skills/README.md",
    ".agents/skills/activation.toml",
    ".agents/skills/ethos-repository-governance/SKILL.md",
    "openspec/config.yaml",
    "openspec/changes/.gitkeep",
    "openspec/changes/archive/.gitkeep",
    "docs/index.md",
    "docs/start/quickstart.md",
    "docs/governance/ethos.md",
    "docs/evidence/.gitkeep",
    "claims/.gitkeep",
)

STATIC_DEFAULT_FILES = {
    ".ethos/rules.toml": """[command_plane]
public = "ethos"

[formats]
user_config = "TOML"
machine_output = "JSON"
append_only_events = "JSONL"
local_state = "SQLite"

[artifacts]
state_path = ".ethos/state/state.sqlite"
state_tracked_truth = false
durable_evidence_roots = ["docs/evidence", "claims"]

[gates]
self_audit = "ethos self audit --json"
report = "ethos report --json"
openspec = "openspec validate --all --strict --json"
""",
    ".ethos/assistants.toml": """[projection]
truth = "repository"
thin_adapter = true

[surfaces]
codex = "projection"
jetbrains = "projection"
mcp = "protocol-projection"
acp = "protocol-projection"
""",
    ".ethos/release.toml": """[release]
version_source = "pyproject.toml"
tag_pattern = "v{version}"

[attestation]
formats = ["in-toto", "slsa", "spdx-lite"]
""",
    ".ethos/state/.gitignore": "*\n!.gitignore\n",
    "openspec/changes/.gitkeep": "",
    "openspec/changes/archive/.gitkeep": "",
    "docs/evidence/.gitkeep": "",
    "claims/.gitkeep": "",
}


def available_profiles() -> tuple[str, ...]:
    return PROFILES


def _workspace_toml(root: Path, profile: str) -> str:
    packages_dir = root / "packages"
    if profile == "monorepo" and packages_dir.exists():
        blocks = []
        for package in sorted(path for path in packages_dir.iterdir() if path.is_dir()):
            blocks.append(
                f'[[package]]\nname = "{package.name}"\n'
                f'path = "packages/{package.name}"\ndomains = ["package"]\n'
            )
        if blocks:
            return "\n".join(blocks)
    return '[[package]]\nname = "root"\npath = "."\ndomains = ["repository"]\n'


def _openspec_config(root: Path) -> str:
    return f"project: {root.name}\nversion: 1\n"


def _openspec_spec(family: str) -> str:
    titles = {
        "ethos-kernel": "Kernel Contract",
        "ethos-project": "Project Adoption",
        "ethos-governance": "Governance And Evidence",
        "ethos-workspace": "Workspace And Release",
        "ethos-agent": "Agentic Projections",
        "ethos-distribution": "Distribution Adapters",
    }
    title = titles[family]
    return f"""# {family}

## Purpose

ETHOS SHALL keep the {title} family cohesive and separate from adopter-specific
semantics.

## Requirements

### Requirement: Family Boundary
The {family} family SHALL describe one bounded product concern.

#### Scenario: Family remains bounded
- **WHEN** ETHOS validates repository governance
- **THEN** {family} requirements are checked without introducing private
  adopter semantics into the product core
"""


def _skills_readme() -> str:
    return """# ETHOS Skills

Repo-local skills are thin playbook projections. They route agents toward
tracked ETHOS commands, docs, schemas, and evidence; they are not an independent
source of truth.
"""


def _skills_activation() -> str:
    return """[meta]
version = 1
source_of_truth = "repository"

[[skill]]
id = "ethos-repository-governance"
path = ".agents/skills/ethos-repository-governance/SKILL.md"
subjects = ["repository-governance", "ethos", "self-governance", "adoption"]
commands = ["ethos status", "ethos plan", "ethos prove", "ethos report"]
boundary = "thin-playbook-projection"
"""


def _governance_skill() -> str:
    return """---
name: ethos-repository-governance
description: Use when governing a repository with ETHOS commands, evidence, and adoption profiles.
---

# ETHOS Repository Governance

Use the `ethos ...` public command plane first:

```bash
ethos status
ethos plan --changed
ethos prove
ethos report
```

This skill is a thin playbook projection. Repository source, tests, schemas,
OpenSpec records, claims, evidence, and ETHOS command output remain the source of truth.
"""


def _docs_index(root: Path) -> str:
    return f"""---
subject: docs:index
role: reference
state: canonical
relations: canonical_for: navigation
---

# {root.name} ETHOS Governance

Start with [Quickstart](start/quickstart.md), then read
[ETHOS Governance](governance/ethos.md).
"""


def _quickstart() -> str:
    return """---
subject: docs:start
role: workflow
state: active
relations: canonical_for: first run
---

# Quickstart

```bash
ethos status
ethos plan --changed
ethos prove
ethos land
ethos publish
```

Use `--json` for stable machine output. Mutating paths require explicit
authorization and expected HEAD binding.
"""


def _governance_doc() -> str:
    return """---
subject: ethos:governance
role: policy
state: canonical
relations: canonical_for: repository governance
---

# ETHOS Governance

ETHOS governs this repository through tracked config, official OpenSpec records,
repo-local skills, claims, evidence, and deterministic command output.

Assistant files and protocol adapters are projections. Host-local memory,
credentials, and runtime state are not repository truth.
"""


def _gitlab_ci() -> str:
    return (
        "stages:\n"
        "  - verify\n\n"
        "ethos:verify:\n"
        "  stage: verify\n"
        "  image: python:3.12\n"
        "  script:\n"
        "    - pip install uv\n"
        "    - npm install -g @fission-ai/openspec\n"
        "    - uv run --group dev pytest tests/unit tests/architecture -q\n"
        "    - uv run --group dev ruff check .\n"
        "    - openspec validate --all --strict --json\n"
        "    - uv run --package ethos ethos self audit --json\n"
        "    - uv run --package ethos ethos report --json\n"
        "    - uv run --package ethos ethos quality release-policy --json\n"
    )


def _default_files(root: Path, profile: str) -> dict[str, str]:
    project_name = json.dumps(root.name)
    files = {
        ".ethos/project.toml": (
            f"[meta]\nname = {project_name}\nproduct = \"ETHOS\"\nversion = 1\n"
        ),
        ".ethos/workspace.toml": _workspace_toml(root, profile),
        "openspec/config.yaml": _openspec_config(root),
        ".agents/skills/README.md": _skills_readme(),
        ".agents/skills/activation.toml": _skills_activation(),
        ".agents/skills/ethos-repository-governance/SKILL.md": _governance_skill(),
        "docs/index.md": _docs_index(root),
        "docs/start/quickstart.md": _quickstart(),
        "docs/governance/ethos.md": _governance_doc(),
        **STATIC_DEFAULT_FILES,
    }
    for family in OPENSPEC_FAMILIES:
        files[f"openspec/specs/{family}/spec.md"] = _openspec_spec(family)
    if profile == "gitlab":
        files[".gitlab-ci.yml"] = _gitlab_ci()
    if profile == "github":
        files[".github/workflows/ethos.yml"] = (
            "name: ethos\non: [push, pull_request]\njobs:\n"
            "  verify:\n    runs-on: ubuntu-latest\n    steps:\n"
            "      - uses: actions/checkout@v4\n      - uses: astral-sh/setup-uv@v5\n"
            "      - run: uv run --group dev pytest tests/unit tests/architecture -q\n"
            "      - run: uv run --package ethos ethos report --json\n"
        )
    return files


def detect_repo_profile(root: Path) -> str:
    if (root / ".gitlab-ci.yml").exists():
        return "gitlab"
    if (root / ".github").exists():
        return "github"
    if (root / "packages").exists():
        return "monorepo"
    if (root / "pyproject.toml").exists():
        return "python-package"
    return "generic"


def adoption_plan(
    root: Path,
    *,
    profile: str | None = None,
    apply: bool = False,
) -> dict[str, object]:
    selected_profile = profile or detect_repo_profile(root)
    if selected_profile not in PROFILES:
        msg = f"unknown ETHOS adoption profile: {selected_profile}"
        raise ValueError(msg)
    files = _default_files(root, selected_profile)
    planned = sorted(files)
    existing = sorted(relative for relative in files if (root / relative).exists())
    if apply:
        for relative, content in files.items():
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and target.read_text(encoding="utf-8") != "":
                continue
            target.write_text(content, encoding="utf-8")
    return {
        "root": str(root),
        "planned_files": planned,
        "applied": apply,
        "profile": selected_profile,
        "available_profiles": list(PROFILES),
        "existing_files": existing,
    }


def adoption_scaffold_report() -> dict[str, object]:
    required = set(BASE_ADOPTION_FILES)
    required.update(f"openspec/specs/{family}/spec.md" for family in OPENSPEC_FAMILIES)
    planned = set(_default_files(Path("sample"), "gitlab"))
    missing = sorted(required - planned)
    return {
        "ok": not missing,
        "required_files": sorted(required),
        "missing": missing,
        "profiles": list(PROFILES),
        "openspec_families": list(OPENSPEC_FAMILIES),
    }
