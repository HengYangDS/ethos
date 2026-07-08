"""Adoption skill and skill-package scaffold generators."""

from __future__ import annotations

import json


def governance_skill() -> str:
    """Return the scaffold text for the governance skill."""
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


def skill_portfolio_skill() -> str:
    """Return the scaffold text for the skill portfolio skill."""
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


def adoption_profile_skill() -> str:
    """Return the scaffold text for the adoption profile skill."""
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


def governance_skill_package(package_digest: str) -> str:
    """Return the scaffold text for the governance skill package."""
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


def skill_portfolio_skill_package(package_digest: str) -> str:
    """Return the scaffold text for the skill portfolio skill package."""
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


def adoption_profile_skill_package(package_digest: str) -> str:
    """Return the scaffold text for the adoption profile skill package."""
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
