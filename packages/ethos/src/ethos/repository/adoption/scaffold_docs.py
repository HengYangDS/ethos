"""Adoption scaffold text templates."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


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
ethos orient
ethos status
ethos plan --changed
ethos prove
ethos land
ethos publish
ethos report
```

`ethos orient` is read-only first-glance UX for humans and agents. It projects
`status` and `report` to show where you are, what you may do, visible foreign
Work Lanes, readiness, and next action. It is not a transition verb and does not
mint repository truth.

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


def _docs_readme(root: Path) -> str:
    return f"""---
subject: docs:root
role: index
state: canonical
relations: canonical_for: documentation navigation
---

# {root.name} Documentation

Status: canonical.

Purpose: route current contracts, decisions, evidence, references, future design,
and history through the common ETHOS-governed documentation topology.

See also: [ETHOS Product Index](index.md), [Current Docs](current/README.md),
[Decision Records](decisions/README.md), [Evidence Docs](evidence/README.md),
and [Reference Docs](reference/README.md).

## Lanes

| Lane | Owns |
| --- | --- |
| `current/` | Implemented contracts, runbooks, and development rules. |
| `decisions/` | Durable rulings with explicit scope and revisit triggers. |
| `evidence/` | Dated proof, manifests, smoke notes, and closeout records. |
| `future/` | Target designs and roadmap material not yet current truth. |
| `reference/` | Stable vocabulary, boundaries, and governance references. |
| `history/` | Retired rationale and archival logs. |

Required kernel paths include `docs/current/README.md`,
`docs/decisions/README.md`, `docs/evidence/README.md`,
`docs/future/README.md`, `docs/history/README.md`, and
`docs/reference/README.md`.
"""


def _docs_current() -> str:
    return """---
subject: docs:current
role: index
state: canonical
relations: canonical_for: current documentation
---

# Current Documentation

Status: canonical.

Purpose: hold implemented behavior, active runbooks, and development governance
for this adopted repository.

See also: [Documentation Index](../README.md), [Evidence Docs](../evidence/README.md),
and [Decision Records](../decisions/README.md).

No detailed current docs are scaffolded yet. Promote implemented contracts here
after they are backed by source, tests, package metadata, or evidence.
"""


def _docs_reference() -> str:
    return """---
subject: docs:reference
role: index
state: canonical
relations: canonical_for: reference documentation
---

# Reference Documentation

Status: canonical.

Purpose: hold stable vocabulary, repository boundaries, and governance references.

See also: [Documentation Index](../README.md), [Current Docs](../current/README.md),
and [ETHOS Governance](../governance/ethos.md).

Reference docs explain terms and boundaries; runtime truth still comes from
source, tests, current docs, and evidence.
"""


def _docs_evidence() -> str:
    return """---
subject: docs:evidence
role: index
state: canonical
relations: canonical_for: evidence documentation
---

# Evidence Documentation

Status: canonical.

Purpose: hold dated proof, manifests, smoke notes, closeout records, and scope
limits for this adopted repository.

See also: [Documentation Index](../README.md), [Current Docs](../current/README.md),
and [Decision Records](../decisions/README.md).

Evidence supports claims; it is not the current API or a generated log dump.
"""


def _docs_future() -> str:
    return """---
subject: docs:future
role: index
state: canonical
relations: canonical_for: future documentation
---

# Future Documentation

Status: canonical.

Purpose: hold target designs and roadmap material that are not yet current truth.

See also: [Documentation Index](../README.md), [Current Docs](../current/README.md),
and [Decision Records](../decisions/README.md).

Future docs must be promoted into source, tests, package metadata, current docs,
or evidence before they can justify runtime claims.
"""


def _docs_history() -> str:
    return """---
subject: docs:history
role: index
state: canonical
relations: canonical_for: historical documentation
---

# History Documentation

Status: canonical.

Purpose: hold retired rationale, archival logs, and migration history.

See also: [Documentation Index](../README.md), [Current Docs](../current/README.md),
and [Reference Docs](../reference/README.md).

History preserves context; it does not override current contracts or evidence.
"""


def _decision_records() -> str:
    return """---
subject: docs:decisions
role: index
state: canonical
relations: canonical_for: decision records
---

# Decision Records

Status: canonical.

Purpose: hold durable repository rulings future agents must respect before
reopening architecture, governance, tooling, or process choices.

See also: [Decision Index](decision-index.md), [Accepted Decisions](accepted/README.md),
[Superseded Decisions](superseded/README.md), and
[Decision Record Template](templates/decision-record.md).

## Choose

| Need | Read |
| --- | --- |
| Current accepted rulings | [Decision Index](decision-index.md) |
| Accepted record files | [Accepted Decisions](accepted/README.md) |
| Superseded record files | [Superseded Decisions](superseded/README.md) |
| Start a new decision record | [Decision Record Template](templates/decision-record.md) |
| Review dependencies | [Decision Dependency Map](decision-dependency-map.md) |
| Review code and check links | [Decision Code Links](decision-code-links.md) |

Decision Records are not a separate truth lane. They bind a decision to scope,
boundary, proof, consequences, and revisit triggers.
"""


def _decision_index() -> str:
    return """---
subject: docs:decisions:index
role: index
state: canonical
relations: canonical_for: decision index
---

# Decision Index

Status: canonical.

Purpose: route current durable repository rulings.

See also: [Decision Records](README.md) and [Accepted Decisions](accepted/README.md).

No accepted repository-specific Decision Records are scaffolded yet.
"""


def _decision_dependency_map() -> str:
    return """---
subject: docs:decisions:dependency-map
role: reference
state: canonical
relations: canonical_for: decision dependency map
---

# Decision Dependency Map

Status: canonical.

Purpose: show dependencies between durable repository rulings.

See also: [Decision Index](decision-index.md).

No decision dependencies are scaffolded yet.
"""


def _decision_code_links() -> str:
    return """---
subject: docs:decisions:code-links
role: reference
state: canonical
relations: canonical_for: decision code links
---

# Decision Code Links

Status: canonical.

Purpose: connect durable rulings to code, tests, commands, and evidence.

See also: [Decision Index](decision-index.md).

No decision code links are scaffolded yet.
"""


def _decisions_accepted() -> str:
    return """---
subject: docs:decisions:accepted
role: index
state: canonical
relations: canonical_for: accepted decision records
---

# Accepted Decision Records

Status: canonical.

Purpose: list accepted durable repository rulings.

See also: [Decision Records](../README.md).

No accepted Decision Records are scaffolded yet.
"""


def _decisions_superseded() -> str:
    return """---
subject: docs:decisions:superseded
role: index
state: canonical
relations: canonical_for: superseded decision records
---

# Superseded Decision Records

Status: canonical.

Purpose: hold decisions that no longer define current repository rulings.

See also: [Accepted Decision Records](../accepted/README.md).

No superseded Decision Records are scaffolded yet.
"""


def _decisions_templates() -> str:
    return """---
subject: docs:decisions:templates
role: index
state: canonical
relations: canonical_for: decision record templates
---

# Decision Record Templates

Status: canonical.

Purpose: provide reusable templates for durable repository rulings.

See also: [Decision Records](../README.md) and [Decision Record Template](decision-record.md).

Use the template when a judgment must bind future work.
"""


def _decision_record_template() -> str:
    return """---
subject: docs:decisions:template
role: template
state: canonical
relations: canonical_for: decision record template
---

# DR-XXXX: Title

Status: proposed.

Purpose: record one durable repository ruling.

See also: [Decision Records](../README.md) and [Decision Index](../decision-index.md).

## Record

| Field | Value |
| --- | --- |
| Decision ID | DR-XXXX |
| Kind | governance |
| Decision Makers | TBD |
| Status | proposed |
| Decision Date | YYYY-MM-DD |
| Scope | TBD |
| Boundary | TBD |
| Decision | TBD |
| Proof or Evidence | TBD |
| Revisit Trigger | TBD |

## Context

TBD.

## Decision

TBD.

## Consequences

TBD.

## Revisit Trigger

TBD.
"""
