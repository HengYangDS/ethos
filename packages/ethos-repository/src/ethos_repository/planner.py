from __future__ import annotations

import hashlib
import json
from pathlib import Path

PROFILES = ("generic", "python-package", "monorepo", "github", "gitlab")
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
    ".agents/skills/ethos-repository-governance/package.toml",
    "openspec/config.yaml",
    "openspec/changes/.gitkeep",
    "openspec/changes/archive/.gitkeep",
    "docs/index.md",
    "docs/start/quickstart.md",
    "docs/governance/ethos.md",
    "docs/evidence/.gitkeep",
    "claims/.gitkeep",
    "schemas/ethos/.gitkeep",
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
    "schemas/ethos/.gitkeep": "",
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


def _capability_profile(family: str) -> str:
    scopes = {
        "ethos-core": "pure kernel result and action graph semantics",
        "ethos-contracts": "provider-neutral repository contracts",
        "ethos-repository": "repository lifecycle governance",
        "ethos-adapters": "provider and projection adapters",
        "ethos-assistants": "assistant and context projection boundaries",
        "ethos-cli": "public ETHOS command plane",
        "ethos-distribution": "distribution and host package surfaces",
        "ethos-test": "conformance, fixture, and parity proof hosts",
    }
    scope = scopes[family]
    return f'''family = "{family}"
primary_invariant = "The {family} family keeps {scope} cohesive and provider-neutral."
routing_question = "Does this change alter {scope}?"
boundary_rules = [
  "OpenSpec records are specification carriers, not truth owners.",
  "Provider or adopter-specific state remains in adapters, profiles, or evidence.",
]

[owner]
package = "{family}"
scope = "{scope}"

[proof_profile]
default_command = "ethos prove --json"
executed_command = "ethos prove --execute --json"
required_gates = ["claims", "schemas"]
'''


def _skills_readme() -> str:
    return """# ETHOS Skills

Repo-local skills are workflow package projections over ETHOS repository truth.
They route agents toward tracked ETHOS commands, docs, schemas, claims, and
evidence; they are not an independent source of truth.
"""


def _skills_activation(package_digest: str) -> str:
    return """[meta]
version = 2
source_of_truth = "repository"

[[skill]]
id = "ethos-repository-governance"
path = ".agents/skills/ethos-repository-governance/SKILL.md"
package_manifest = ".agents/skills/ethos-repository-governance/package.toml"
subject = "repository-governance"
operation = "govern"
authority = "primary"
lifecycle = "active"
subjects = ["repository-governance", "ethos", "self-governance", "adoption", "changed-scope"]
path_globs = [
  "AGENTS.md",
  ".ethos/**",
  ".agents/skills/**",
  "docs/**",
  "openspec/**",
  "claims/**",
  "packages/**",
  "schemas/**",
  "tests/**",
  "uv.lock",
  "pyproject.toml",
]
intent_tokens = ["ethos", "governance", "proof", "adoption", "skills"]
pre_reads = ["AGENTS.md", "docs/governance/ethos.md"]
during_rules = [
  "treat skills as projections over repository truth",
  "use ETHOS command JSON as machine evidence",
]
post_checks = ["ethos playbooks check --mode v2-strict --json", "ethos report --json"]
commands = ["ethos status", "ethos plan", "ethos prove", "ethos report"]
boundary = "workflow-package-projection"
"""


def _governance_skill() -> str:
    return """---
name: ethos-repository-governance
description: Use when governing a repository with ETHOS commands, evidence, and adoption profiles.
---

# ETHOS Repository Governance

## When to Use

Use this skill when governing an ETHOS-adopted repository, changing repository
governance files, planning proof, or validating adoption readiness.

## Workflow

1. Read `AGENTS.md` and the current governance docs for the target repository.
2. Run `ethos status --json` to classify checkout role and required gaps.
3. Use `ethos plan --changed --json` or `ethos playbooks route --changed --json`
   to select the focused governance path.
4. Run the narrow proof command first, then `ethos report --json` before
   claiming readiness.

## Evidence

Use the `ethos ...` public command plane for machine-readable evidence:

```bash
ethos status --json
ethos plan --changed --json
ethos prove --json
ethos report --json
```

## Trust Boundary

This skill is a workflow package projection. Repository source, tests, schemas,
OpenSpec records, claims, evidence, and ETHOS command JSON remain the source of truth.
"""


def _governance_skill_package(package_digest: str) -> str:
    return f"""schema_version = 2
id = "ethos-repository-governance"
entrypoint = "SKILL.md"
boundary = "workflow-package-projection"
truth = "repository-source-and-contracts"
digest_algorithm = "sha256"
include = ["SKILL.md"]
exclude = [".DS_Store"]
expected_digest = "{package_digest}"
required_sections = ["When to Use", "Workflow", "Evidence", "Trust Boundary"]

[quality]
official_codex_loadable = true
placeholder_allowed = false

[[capability]]
id = "ethos.status"
kind = "command_readonly"
command = ["ethos", "status", "--json"]

[[capability]]
id = "ethos.plan"
kind = "command_readonly"
command = ["ethos", "plan", "--changed", "--json"]

[[capability]]
id = "ethos.report"
kind = "command_readonly"
command = ["ethos", "report", "--json"]

[[capability]]
id = "ethos.prove"
kind = "command_proof"
command = ["ethos", "prove", "--json"]
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
ethos prove --execute
ethos quality command-examples
ethos land
ethos publish
```

Use `--json` for stable machine output. Mutating paths require explicit
authorization and expected HEAD binding.
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
ethos prove --execute
ethos quality command-examples
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
    governance_skill = _governance_skill()
    package_digest = _package_digest_from_content({"SKILL.md": governance_skill})
    files = {
        "AGENTS.md": _agents_doc(),
        "CONTRIBUTING.md": _contributing_doc(),
        "CHANGELOG.md": _changelog_doc(),
        ".ethos/project.toml": (f'[meta]\nname = {project_name}\nproduct = "ETHOS"\nversion = 1\n'),
        ".ethos/workspace.toml": _workspace_toml(root, profile),
        ".ethos/release.toml": _release_toml(profile),
        "openspec/config.yaml": _openspec_config(root),
        ".agents/skills/README.md": _skills_readme(),
        ".agents/skills/activation.toml": _skills_activation(package_digest),
        ".agents/skills/ethos-repository-governance/SKILL.md": governance_skill,
        ".agents/skills/ethos-repository-governance/package.toml": (
            _governance_skill_package(package_digest)
        ),
        "docs/index.md": _docs_index(root),
        "docs/start/quickstart.md": _quickstart(),
        "docs/governance/ethos.md": _governance_doc(),
        **STATIC_DEFAULT_FILES,
    }
    for family in OPENSPEC_FAMILIES:
        files[f"openspec/specs/{family}/spec.md"] = _openspec_spec(family)
        files[f"openspec/specs/{family}/capability.toml"] = _capability_profile(family)
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


def _package_digest_from_content(files: dict[str, str]) -> str:
    digest = hashlib.sha256()
    for relative, content in sorted(files.items()):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content.encode("utf-8"))
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


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
    required.update(f"openspec/specs/{family}/capability.toml" for family in OPENSPEC_FAMILIES)
    planned = set(_default_files(Path("sample"), "gitlab"))
    missing = sorted(required - planned)
    return {
        "ok": not missing,
        "required_files": sorted(required),
        "missing": missing,
        "profiles": list(PROFILES),
        "openspec_families": list(OPENSPEC_FAMILIES),
    }
