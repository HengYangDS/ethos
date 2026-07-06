"""Adoption scaffold file builders."""

from __future__ import annotations

import hashlib
import json
import tomllib
from typing import TYPE_CHECKING

from ethos_core.contracts.skill_activation import normalize_skill_activation
from ethos_core.contracts.skill_activation import skill_registry_digest

if TYPE_CHECKING:
    from pathlib import Path

OPENSPEC_FAMILIES = (
    "ethos-core",
    "ethos-contracts",
    "ethos-quality",
    "ethos-repository",
    "ethos-adapters",
    "ethos-assistants",
    "ethos-cli",
    "ethos-distribution",
    "ethos-test",
)
if len(OPENSPEC_FAMILIES) != len(set(OPENSPEC_FAMILIES)):
    msg = "OPENSPEC_FAMILIES contains duplicate entries"
    raise ValueError(msg)
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
    ".agents/skills/ethos-skill-portfolio-governance/SKILL.md",
    ".agents/skills/ethos-skill-portfolio-governance/package.toml",
    ".agents/skills/ethos-adoption-profile-governance/SKILL.md",
    ".agents/skills/ethos-adoption-profile-governance/package.toml",
    "openspec/config.yaml",
    "openspec/README.md",
    "openspec/specs/README.md",
    "openspec/specs/families.toml",
    "openspec/specs/capability.template.toml",
    "openspec/changes/README.md",
    "openspec/changes/template.md",
    "openspec/changes/.gitkeep",
    "openspec/changes/archive/.gitkeep",
    "docs/index.md",
    "docs/start/quickstart.md",
    "docs/governance/ethos.md",
    "evidence/.gitkeep",
    "evidence/claims/.gitkeep",
    "system/schemas/kernel/.gitkeep",
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
durable_evidence_roots = ["evidence", "evidence/claims"]

[gates]
governance_audit = "ethos report --json"
proof = "ethos prove --json"
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
    "evidence/.gitkeep": "",
    "evidence/claims/.gitkeep": "",
    "system/schemas/kernel/.gitkeep": "",
}


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


def _openspec_readme() -> str:
    return """# OpenSpec Workspace

This workspace is the ETHOS case and specification carrier. Use `ethos ...` as
the public workflow and let ETHOS call the official OpenSpec CLI for strict
validation when specification health must be proved.

Cases are active changes under `openspec/changes/<change-id>/` with proposal,
design, tasks, spec deltas, claim binding, and evidence refs. Accepted behavior
lives under `openspec/specs/<capability>/spec.md` after promotion.
"""


def _openspec_specs_readme() -> str:
    return """# OpenSpec Capability Specs

Each capability directory contains accepted behavior in `spec.md` and ETHOS
routing metadata in `capability.toml`. Proposal capability entries must name
live capability directories exactly; aliases are diagnostic only.
"""


def _openspec_changes_readme() -> str:
    return """# OpenSpec Changes

Active changes are ETHOS case carriers. They record intended change and review
state; they do not supersede source, tests, schemas, docs, accepted specs,
claims, or evidence until closeout promotes those surfaces.

Use `template.md` when authoring non-trivial governance changes and validate
with `ethos openspec --lifecycle --json`.
"""


def _openspec_families() -> str:
    return """[families.kernel]
description = "Pure ETHOS kernel contracts, result envelopes, and provider-neutral semantics."

[families.contracts]
description = "Schemas, TOML contracts, evidence envelopes, and command JSON contracts."

[families.repository-governance]
description = "Repository lifecycle, Work Lanes, claims, evidence, campaigns, and OpenSpec cases."

[families.adapters]
description = "Provider adapters for Git, process, OpenSpec, hosted CI, and protocols."

[families.surfaces]
description = "CLI, MCP, SDK, skill, assistant, host, and distribution surfaces."

[families.quality]
description = "Quality policy, deterministic proof, docs consistency, gates, and assets."

[families.proof]
description = "Conformance, fixtures, parity, closeout evidence, and proof-host behavior."
"""


def _openspec_capability_template() -> str:
    return """family = "repository-governance"
primary_invariant = "State the one behavior this capability protects."
routing_question = "Ask the question that selects this capability over peers."
decision_axes = ["lifecycle", "surface", "authority"]
boundary_rules = ["Name what this capability must not absorb."]
aliases = []

[owner]
package = "ethos-repository"
scope = "repository lifecycle governance"

[recommended_facets]
lifecycle = ["authoring", "validation", "runtime", "archive", "release"]
surface = ["cli", "docs", "schema", "openspec", "evidence"]
authority = ["source", "test", "schema", "docs", "openspec", "claim", "evidence"]

[proof_profile]
default_command = "ethos prove --json"
executed_command = "ethos prove --execute --json"
required_gates = ["claims", "schemas"]
"""


def _openspec_change_template() -> str:
    return """# Change Template

Create `proposal.md`, `design.md`, `tasks.md`, and `specs/<capability>/spec.md`
under `openspec/changes/<change-id>/`.

Proposal capability entries must include:

```text
capability=<live-capability>
subject=<stable-subject>
reuse=<reuse|extend|extract|new>
change=<add|modify|remove|rename|retire>
facet:lifecycle=<authoring|validation|runtime|archive|release>
facet:surface=<cli|docs|schema|openspec|evidence|skill|mcp|scaffold|ci|package>
facet:authority=<source|test|schema|docs|openspec|claim|evidence>
```
"""


def _openspec_spec(family: str) -> str:
    titles = {
        "ethos-core": "Pure Kernel",
        "ethos-contracts": "Provider-neutral Contracts",
        "ethos-quality": "Quality And Determinism",
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
        "ethos-quality": "quality, determinism, docs profile, and proof policy",
        "ethos-repository": "repository lifecycle governance",
        "ethos-adapters": "provider and projection adapters",
        "ethos-assistants": "assistant and context projection boundaries",
        "ethos-cli": "public ETHOS command plane",
        "ethos-distribution": "distribution and host package surfaces",
        "ethos-test": "conformance, fixture, and parity proof hosts",
    }
    profile_families = {
        "ethos-core": "kernel",
        "ethos-contracts": "contracts",
        "ethos-quality": "quality",
        "ethos-repository": "repository-governance",
        "ethos-adapters": "adapters",
        "ethos-assistants": "surfaces",
        "ethos-cli": "surfaces",
        "ethos-distribution": "surfaces",
        "ethos-test": "proof",
    }
    scope = scopes[family]
    return f'''family = "{profile_families[family]}"
primary_invariant = "The {family} family keeps {scope} cohesive and provider-neutral."
routing_question = "Does this change alter {scope}?"
decision_axes = ["lifecycle", "surface", "authority"]
boundary_rules = [
  "OpenSpec records are specification carriers, not truth owners.",
  "Provider or adopter-specific state remains in adapters, profiles, or evidence.",
]
aliases = []

[owner]
package = "{family}"
scope = "{scope}"

[recommended_facets]
lifecycle = ["authoring", "validation", "runtime"]
surface = ["cli", "docs", "schema", "openspec", "evidence"]
authority = ["source", "test", "schema", "docs", "openspec", "claim", "evidence"]

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

## Available Skills

| Skill | Use when |
| --- | --- |
| ethos-repository-governance | Governing repository truth, authority, proof, docs, and adoption. |
| ethos-skill-portfolio-governance | Creating, routing, validating, or retiring repo-local skills. |
| ethos-adoption-profile-governance | Applying profiles and preserving command isomorphism. |
"""


def _skills_activation(registry_digest: str) -> str:
    return f"""[meta]
version = 2
source_of_truth = "repository"
expected_registry_digest = "{registry_digest}"

[[skill]]
id = "ethos-repository-governance"
path = ".agents/skills/ethos-repository-governance/SKILL.md"
package_manifest = ".agents/skills/ethos-repository-governance/package.toml"
subject = "repository-governance"
operation = "govern"
authority = "primary"
lifecycle = "active"
subjects = ["repository-governance", "ethos", "adoption", "changed-scope"]
path_globs = [
  "AGENTS.md",
  "docs/index.md",
  "docs/start/**",
  "evolution/**",
  "evidence/claims/**",
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

[[skill]]
id = "ethos-skill-portfolio-governance"
path = ".agents/skills/ethos-skill-portfolio-governance/SKILL.md"
package_manifest = ".agents/skills/ethos-skill-portfolio-governance/package.toml"
subject = "skill-portfolio"
operation = "govern"
authority = "primary"
lifecycle = "active"
subjects = ["skill-portfolio", "skills", "activation", "projection-drift", "changed-scope"]
path_globs = [".agents/skills/**"]
intent_tokens = ["skill", "skills", "meta-skill", "playbook", "activation", "projection"]
pre_reads = ["AGENTS.md", ".agents/skills/README.md"]
during_rules = [
  "add a skill only for repeated repository-specific procedure",
  "keep SKILL.md narrow and evidence-bound",
]
post_checks = ["ethos playbooks check --mode v2-strict --json", "ethos report --json"]
may_coactivate = ["ethos-repository-governance"]
commands = ["ethos playbooks check", "ethos playbooks route", "ethos report"]
boundary = "workflow-package-projection"

[[skill]]
id = "ethos-adoption-profile-governance"
path = ".agents/skills/ethos-adoption-profile-governance/SKILL.md"
package_manifest = ".agents/skills/ethos-adoption-profile-governance/package.toml"
subject = "adoption-profile"
operation = "adopt"
authority = "primary"
lifecycle = "active"
subjects = ["adoption-profile", "adoption", "profile", "adapter", "changed-scope"]
path_globs = [".ethos/**", "docs/governance/**", "openspec/**", ".gitlab-ci.yml", ".github/**"]
intent_tokens = ["adopt", "adoption", "profile", "adapter", "other repository"]
pre_reads = ["AGENTS.md", "docs/governance/ethos.md"]
during_rules = [
  "profile changes proof depth and adapters, not command semantics",
  "durable adopter truth must be promoted into tracked repository surfaces",
]
post_checks = ["ethos playbooks check --mode v2-strict --json", "ethos report --json"]
may_coactivate = ["ethos-repository-governance"]
commands = ["ethos adopt", "ethos status", "ethos playbooks check", "ethos report", "ethos prove"]
boundary = "workflow-package-projection"
"""


def _skills_activation_with_digest() -> str:
    placeholder = "sha256:" + ("0" * 64)
    activation = _skills_activation(placeholder)
    registry = normalize_skill_activation(
        tomllib.loads(activation), source=".agents/skills/activation.toml"
    )
    return _skills_activation(skill_registry_digest(registry))


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
ethos land --json
ethos publish --json
ethos report --json
```

## Trust Boundary

This skill is a workflow package projection. Repository source, tests, schemas,
OpenSpec records, claims, evidence, and ETHOS command JSON remain the source of truth.
"""


def _skill_portfolio_skill() -> str:
    return """---
name: ethos-skill-portfolio-governance
description: Use when governing repo-local ETHOS skills.
---

# ETHOS Skill Portfolio Governance

## When to Use

Use this skill when changing repo-local skills, activation routing, package
manifests, or provider projections. It is a meta-skill over skill procedures,
not a replacement for repository truth.

## Workflow

1. Read `AGENTS.md` and `.agents/skills/README.md`.
2. Add or update a skill only when a repeated repository-specific procedure would
   otherwise be missed.
3. Keep `SKILL.md` narrow: trigger, workflow, evidence, and trust boundary.
4. Update activation and package manifest metadata together.
5. Run strict playbook checks before claiming readiness.

## Evidence

Use ETHOS command JSON:

```bash
ethos playbooks check --mode v2-strict --json
ethos playbooks route --changed --json
ethos report --json
```

## Trust Boundary

Repository truth remains the source of truth. Skills are workflow projections
over tracked source, tests, schemas, docs, OpenSpec records, claims, evidence,
and ETHOS command JSON.
"""


def _adoption_profile_skill() -> str:
    return """---
name: ethos-adoption-profile-governance
description: Use when applying ETHOS profiles or adapter boundaries.
---

# ETHOS Adoption Profile Governance

## When to Use

Use this skill when ETHOS governs this repository through an adoption profile,
changes scaffolded governance, or checks product/adopter command isomorphism.

## Workflow

1. Treat the governed subject as a Git repository.
2. Use `ethos status --json`, `ethos report --json`, and profile-appropriate
   proof to expose the current boundary.
3. Keep provider state in adapters and projections.
4. Promote durable truth into tracked source, docs, schemas, OpenSpec, claims,
   or evidence.
5. Validate strict playbooks before claiming adoption readiness.

## Evidence

Use shared ETHOS commands:

```bash
ethos status --json
ethos playbooks check --mode v2-strict --json
ethos report --json
ethos prove --json
```

## Trust Boundary

Repository truth remains the source of truth. This skill routes adoption work;
hosted forges, CI, MCP, editor state, and generated assistant surfaces are
adapters or projections.
"""


def _skill_package(skill_id: str, package_digest: str, capabilities: tuple[str, ...]) -> str:
    capability_blocks = "\n".join(capabilities)
    return f"""schema_version = 2
id = "{skill_id}"
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

{capability_blocks}
"""


def _governance_skill_package(package_digest: str) -> str:
    return _skill_package(
        "ethos-repository-governance",
        package_digest,
        (
            _command_capability("ethos.status", "command_readonly", ["ethos", "status", "--json"]),
            _command_capability(
                "ethos.plan", "command_readonly", ["ethos", "plan", "--changed", "--json"]
            ),
            _command_capability("ethos.report", "command_readonly", ["ethos", "report", "--json"]),
            _command_capability("ethos.prove", "command_proof", ["ethos", "prove", "--json"]),
        ),
    )


def _skill_portfolio_skill_package(package_digest: str) -> str:
    return _skill_package(
        "ethos-skill-portfolio-governance",
        package_digest,
        (
            _command_capability(
                "ethos.playbooks.check",
                "command_readonly",
                ["ethos", "playbooks", "check", "--mode", "v2-strict", "--json"],
            ),
            _command_capability(
                "ethos.playbooks.route",
                "command_readonly",
                ["ethos", "playbooks", "route", "--changed", "--json"],
            ),
            _command_capability("ethos.report", "command_readonly", ["ethos", "report", "--json"]),
        ),
    )


def _adoption_profile_skill_package(package_digest: str) -> str:
    return _skill_package(
        "ethos-adoption-profile-governance",
        package_digest,
        (
            _command_capability(
                "ethos.adopt",
                "command_mutation_guarded",
                ["ethos", "adopt", "--json"],
                guard=(
                    "read-only unless --apply and --authorize are present; "
                    "apply requires explicit head-bound authorization"
                ),
            ),
            _command_capability("ethos.status", "command_readonly", ["ethos", "status", "--json"]),
            _command_capability(
                "ethos.playbooks.check",
                "command_readonly",
                ["ethos", "playbooks", "check", "--mode", "v2-strict", "--json"],
            ),
            _command_capability("ethos.report", "command_readonly", ["ethos", "report", "--json"]),
            _command_capability("ethos.prove", "command_proof", ["ethos", "prove", "--json"]),
        ),
    )


def _command_capability(
    capability_id: str, kind: str, command: list[str], *, guard: str = ""
) -> str:
    rendered = ", ".join(json.dumps(part) for part in command)
    block = (
        "[[capability]]\n"
        f"id = {json.dumps(capability_id)}\n"
        f"kind = {json.dumps(kind)}\n"
        f"command = [{rendered}]"
    )
    if guard:
        block += f"\nguard = {json.dumps(guard)}"
    return block + "\n"


def _docs_index(root: Path) -> str:
    return f"""---
subject: docs:index
role: reference
state: canonical
relations: canonical_for: navigation
---

# {root.name} ETHOS Governance

Status: canonical.

Purpose: provide the adopted repository's ETHOS documentation map.

See also: [Quickstart](start/quickstart.md) and
[ETHOS Governance](governance/ethos.md).

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

Status: active.

Purpose: give the adopted repository a first-run ETHOS command path.

See also: [Documentation Index](../index.md) and
[ETHOS Governance](../governance/ethos.md).

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

Status: canonical.

Purpose: define the adopted repository's ETHOS governance boundary.

See also: [Documentation Index](../index.md) and
[Quickstart](../start/quickstart.md).

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
1. Evidence under `evidence/`.
1. Repo-local skills under `skills/`.

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
        "    - uv run --package ethos ethos report --json\n"
        "    - uv run --package ethos ethos prove --json\n"
        "    - uv run --package ethos ethos quality release-policy --json\n"
    )


def _default_files(root: Path, profile: str) -> dict[str, str]:
    project_name = json.dumps(root.name)
    governance_skill = _governance_skill()
    skill_portfolio_skill = _skill_portfolio_skill()
    adoption_profile_skill = _adoption_profile_skill()
    governance_digest = _package_digest_from_content({"SKILL.md": governance_skill})
    skill_portfolio_digest = _package_digest_from_content({"SKILL.md": skill_portfolio_skill})
    adoption_profile_digest = _package_digest_from_content({"SKILL.md": adoption_profile_skill})
    files = {
        "AGENTS.md": _agents_doc(),
        "CONTRIBUTING.md": _contributing_doc(),
        "CHANGELOG.md": _changelog_doc(),
        ".ethos/project.toml": (f'[meta]\nname = {project_name}\nproduct = "ETHOS"\nversion = 1\n'),
        ".ethos/workspace.toml": _workspace_toml(root, profile),
        ".ethos/release.toml": _release_toml(profile),
        "openspec/config.yaml": _openspec_config(root),
        "openspec/README.md": _openspec_readme(),
        "openspec/specs/README.md": _openspec_specs_readme(),
        "openspec/specs/families.toml": _openspec_families(),
        "openspec/specs/capability.template.toml": _openspec_capability_template(),
        "openspec/changes/README.md": _openspec_changes_readme(),
        "openspec/changes/template.md": _openspec_change_template(),
        ".agents/skills/README.md": _skills_readme(),
        ".agents/skills/activation.toml": _skills_activation_with_digest(),
        ".agents/skills/ethos-repository-governance/SKILL.md": governance_skill,
        ".agents/skills/ethos-repository-governance/package.toml": (
            _governance_skill_package(governance_digest)
        ),
        ".agents/skills/ethos-skill-portfolio-governance/SKILL.md": skill_portfolio_skill,
        ".agents/skills/ethos-skill-portfolio-governance/package.toml": (
            _skill_portfolio_skill_package(skill_portfolio_digest)
        ),
        ".agents/skills/ethos-adoption-profile-governance/SKILL.md": adoption_profile_skill,
        ".agents/skills/ethos-adoption-profile-governance/package.toml": (
            _adoption_profile_skill_package(adoption_profile_digest)
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
