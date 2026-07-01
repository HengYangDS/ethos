from __future__ import annotations

import hashlib
import json
from pathlib import Path

PROFILES = ("generic", "python", "monorepo", "github", "gitlab")
PROFILE_ALIASES = {"python-package": "python"}
PROFILE_READ_FILES = {
    "generic": (".git", ".gitignore", "README.md"),
    "python": ("pyproject.toml", "uv.lock", "noxfile.py", "pytest.ini", "ruff.toml"),
    "monorepo": ("packages", "pyproject.toml", "package.json"),
    "github": (".github/workflows", ".git/config"),
    "gitlab": (".gitlab-ci.yml", ".gitlab", ".git/config"),
}
PROFILE_MATCH_REQUIRED = {
    "generic": (),
    "python": ("pyproject.toml",),
    "monorepo": ("packages",),
    "github": (".github",),
    "gitlab": (".gitlab-ci.yml", ".gitlab"),
}
APPLY_CRITERIA = (
    "profile matches the repository shape",
    "planned_files contains only expected ETHOS governance files",
    "hosted CI and remote publication remain projections until externally proven",
    "rollback path is understood before apply",
)
OPENSPEC_FAMILIES = (
    "ethos-core",
    "ethos-contracts",
    "ethos-repository",
    "ethos-adapters",
    "ethos-assistants",
    "ethos-cli",
    "ethos-distribution",
    "ethos-test",
)
assert len(OPENSPEC_FAMILIES) == len(set(OPENSPEC_FAMILIES))
BASE_ADOPTION_FILES = (
    "AGENTS.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
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
    ".ethos/state/.gitignore": "*\n!.gitignore\n",
    "openspec/changes/.gitkeep": "",
    "openspec/changes/archive/.gitkeep": "",
    "docs/evidence/.gitkeep": "",
    "claims/.gitkeep": "",
}


def available_profiles() -> tuple[str, ...]:
    return PROFILES


def _canonical_profile(profile: str) -> str:
    return PROFILE_ALIASES.get(profile, profile)


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
        "ethos-core": "Pure Kernel",
        "ethos-contracts": "Provider-neutral Contracts",
        "ethos-repository": "Repository Lifecycle Governance",
        "ethos-adapters": "Provider Adapters",
        "ethos-assistants": "Assistant And Context Boundaries",
        "ethos-cli": "Public Command Plane",
        "ethos-distribution": "Distribution Adapters",
        "ethos-test": "Conformance And Parity Proof",
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
ethos land
ethos publish
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

## First Hour

```bash
ethos status
ethos plan --changed
ethos prove
ethos land
ethos publish
ethos report
```

Use `ethos adopt --dry-run --json` to review the profile, write plan, apply
criteria, and rollback list before changing files. Use `ethos adopt --apply
--authorize --expect-head <HEAD> --json` only after the dry-run plan is
acceptable.

`ethos report` is the read-only scorecard for proof status, local land/publish
readiness, hosted evidence separation, and the next action.

## Maintainer Reference

Use `--json` for stable machine output. Mutating paths require explicit
authorization and expected HEAD binding. Maintainer diagnostics such as quality
checks are reference workflows, not the first-hour product path.
"""


def _governance_doc() -> str:
    return """---
subject: ethos:repository-governance
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


def _agents_doc() -> str:
    return """# Agent Entry Point

ETHOS governs this repository through source, tests, schemas, docs, evidence,
OpenSpec records, and the `ethos ...` command plane.

## Authority

1. User instruction.
1. Repository source code, tests, schemas, and package metadata.
1. Canonical docs under `docs/`.
1. Evidence under `docs/evidence/`.
1. Repo-local skills under `.agents/skills/`.

## Operating Rules

- Use `ethos ...` as the public command vocabulary.
- Treat assistant, MCP, ACP, and hosted CI files as projections or adapters.
- Do not treat `.ethos/state/` as tracked truth.
- Write tests for behavior changes.
"""


def _contributing_doc() -> str:
    return """# Contributing

Use the ETHOS command plane for local repository changes:

```bash
ethos status
ethos plan --changed
ethos prove
ethos land
ethos publish
ethos report
```

Mutating operations such as `ethos land` and `ethos publish` require explicit
authorization and expected HEAD binding.
"""


def _changelog_doc() -> str:
    return """# Changelog

## Unreleased

- Adopted ETHOS governance scaffold.
"""


def _release_toml(profile: str) -> str:
    text = """[release]
version_source = "pyproject.toml"
tag_pattern = "v{version}"

[attestation]
formats = ["in-toto", "slsa", "spdx-lite"]
"""
    if profile == "gitlab":
        text += """
[host_profile]
provider = "gitlab"

[host_profile.surfaces]
ci = ".gitlab-ci.yml"
"""
    if profile == "github":
        text += """
[host_profile]
provider = "github"

[host_profile.surfaces]
ci = ".github/workflows/ethos.yml"
"""
    return text


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
        "AGENTS.md": _agents_doc(),
        "CONTRIBUTING.md": _contributing_doc(),
        "CHANGELOG.md": _changelog_doc(),
        ".ethos/project.toml": (
            f"[meta]\nname = {project_name}\nproduct = \"ETHOS\"\nversion = 1\n"
        ),
        ".ethos/workspace.toml": _workspace_toml(root, profile),
        ".ethos/release.toml": _release_toml(profile),
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
        return "python"
    return "generic"


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _observed_files(root: Path, profile: str) -> dict[str, bool]:
    return {relative: (root / relative).exists() for relative in PROFILE_READ_FILES[profile]}


def _profile_match(root: Path, profile: str, detected_profile: str) -> dict[str, object]:
    if profile == "generic":
        return {"ok": True, "reasons": ["matched:generic"]}
    required = PROFILE_MATCH_REQUIRED[profile]
    if profile == detected_profile or any((root / relative).exists() for relative in required):
        return {"ok": True, "reasons": [f"matched:{profile}"]}
    reasons = [f"detected:{detected_profile}"]
    reasons.extend(f"missing:{relative}" for relative in required)
    return {"ok": False, "reasons": reasons}


def _write_plan(root: Path, files: dict[str, str]) -> list[dict[str, object]]:
    plan: list[dict[str, object]] = []
    for relative in sorted(files):
        content = files[relative]
        target = root / relative
        existed = target.exists()
        conflict = False
        if not existed:
            action = "create"
        else:
            existing = target.read_text(encoding="utf-8")
            if existing == content:
                action = "keep_existing"
            elif existing == "":
                action = "write_empty"
            else:
                action = "skip_existing_nonempty"
                conflict = True
        plan.append(
            {
                "path": relative,
                "action": action,
                "conflict": conflict,
                "existed": existed,
                "content_sha256": _sha256_text(content),
                "preview": content.splitlines()[0] if content.splitlines() else "",
            }
        )
    return plan


def adoption_plan(
    root: Path,
    *,
    profile: str | None = None,
    apply: bool = False,
) -> dict[str, object]:
    requested_profile = profile or detect_repo_profile(root)
    selected_profile = _canonical_profile(requested_profile)
    if selected_profile not in PROFILES:
        msg = f"unknown ETHOS adoption profile: {selected_profile}"
        raise ValueError(msg)
    detected_profile = detect_repo_profile(root)
    observed = _observed_files(root, selected_profile)
    profile_match = _profile_match(root, selected_profile, detected_profile)
    files = _default_files(root, selected_profile)
    planned = sorted(files)
    existing = sorted(relative for relative in files if (root / relative).exists())
    write_plan = _write_plan(root, files)
    conflict_gaps = [
        f"adoption_conflict:{item['path']}" for item in write_plan if item["conflict"]
    ]
    profile_ok = bool(profile_match["ok"])
    required_gaps = list(conflict_gaps)
    if apply and not profile_ok:
        required_gaps.append(f"profile_mismatch:{selected_profile}")
    generated_files = sorted(
        str(item["path"]) for item in write_plan if not bool(item["existed"])
    )
    applied = bool(apply and not required_gaps)
    if applied:
        for relative, content in files.items():
            item = next(entry for entry in write_plan if entry["path"] == relative)
            if item["action"] == "keep_existing":
                continue
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
    if conflict_gaps:
        next_action = "resolve adoption conflicts before apply"
    elif not profile_ok:
        next_action = "review profile mismatch before apply"
    elif applied:
        next_action = "ethos status"
    else:
        next_action = "review dry-run write plan"
    return {
        "root": str(root),
        "planned_files": planned,
        "read_files": list(PROFILE_READ_FILES[selected_profile]),
        "observed_files": observed,
        "applied": applied,
        "profile": selected_profile,
        "detected_profile": detected_profile,
        "profile_match": profile_match,
        "requested_profile": requested_profile,
        "profile_aliases": sorted(
            alias for alias, target in PROFILE_ALIASES.items() if target == selected_profile
        ),
        "available_profiles": list(PROFILES),
        "existing_files": existing,
        "write_plan": write_plan,
        "apply_criteria": list(APPLY_CRITERIA),
        "required_gaps": required_gaps,
        "next_action": next_action,
        "rollback": {
            "mode": "remove_generated_files_or_restore_git_state",
            "planned_files": planned,
            "generated_files": generated_files,
        },
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
