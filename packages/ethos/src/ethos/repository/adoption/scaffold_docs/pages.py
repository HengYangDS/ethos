"""Adoption documentation-page scaffold generators."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def docs_index(root: Path) -> str:
    """Return the scaffold text for the docs index documentation page."""
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


def quickstart() -> str:
    """Return the scaffold text for the quickstart guide."""
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


def governance_doc() -> str:
    """Return the scaffold text for governance doc."""
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


def agents_doc() -> str:
    """Return the scaffold text for agents doc."""
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


def contributing_doc() -> str:
    """Return the scaffold text for contributing doc."""
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


def changelog_doc() -> str:
    """Return the scaffold text for changelog doc."""
    return """# Changelog

## Unreleased

- Adopted ETHOS governance scaffold.
"""


def release_toml(profile: str) -> str:
    """Return the scaffold release.toml text for the given profile."""
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


def docs_readme(root: Path) -> str:
    """Return the scaffold text for the docs readme documentation page."""
    return f"""---
subject: docs:root
role: index
state: canonical
relations: canonical_for: documentation navigation
---

# {root.name} Documentation

Status: canonical.

Purpose: route governance, decisions, evidence, plans, references, and history
through the common ETHOS-governed semantic documentation topology.

See also: [ETHOS Product Index](index.md), [Quickstart](start/quickstart.md),
[Governance Docs](governance/README.md), [Decision Records](decisions/README.md),
[Evidence Docs](evidence/README.md), and [Reference Docs](reference/README.md).

## Semantic Lanes

| Lane | Owns |
| --- | --- |
| `start/` | First-run workflows and operator entrypoints. |
| `governance/` | Policies, rules, operating constraints, and ETHOS boundary. |
| `decisions/` | Durable rulings with explicit scope and revisit triggers. |
| `evidence/` | Dated proof, manifests, smoke notes, and closeout records. |
| `plans/` | Planned work and roadmap material with explicit front matter state. |
| `reference/` | Stable vocabulary, boundaries, and command references. |
| `history/` | Retired rationale and archival logs. |

Truth state is declared in document metadata such as `state: canonical`,
`state: active`, or `state: planned`; it is not encoded as `current/` or
`future/` path topology.

Required kernel paths include `docs/index.md`, `docs/start/quickstart.md`,
`docs/governance/README.md`, `docs/decisions/README.md`,
`docs/evidence/README.md`, `docs/plans/README.md`, `docs/history/README.md`,
and `docs/reference/README.md`.
"""


def docs_governance() -> str:
    """Return the scaffold text for the docs governance documentation page."""
    return """---
subject: docs:governance
role: index
state: canonical
relations: canonical_for: governance documentation
---

# Governance Documentation

Status: canonical.

Purpose: route policies, operating constraints, and ETHOS governance boundary
material for this adopted repository.

See also: [Documentation Index](../README.md), [Quickstart](../start/quickstart.md),
[ETHOS Governance](ethos.md), [Evidence Docs](../evidence/README.md), and
[Decision Records](../decisions/README.md).

Promoted governance truth must be backed by source, tests, package metadata,
evidence, or accepted decisions. Planned material belongs under `docs/plans/`
with explicit front matter state until promoted.
"""


def docs_reference() -> str:
    """Return the scaffold text for the docs reference documentation page."""
    return """---
subject: docs:reference
role: index
state: canonical
relations: canonical_for: reference documentation
---

# Reference Documentation

Status: canonical.

Purpose: hold stable vocabulary, repository boundaries, and governance references.

See also: [Documentation Index](../README.md), [Governance Docs](../governance/README.md),
and [ETHOS Governance](../governance/ethos.md).

Reference docs explain terms and boundaries; runtime truth still comes from
source, tests, state-marked canonical docs, and evidence.
"""


def docs_evidence() -> str:
    """Return the scaffold text for the docs evidence documentation page."""
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

See also: [Documentation Index](../README.md), [Governance Docs](../governance/README.md),
and [Decision Records](../decisions/README.md).

Evidence supports claims; it is not the current API or a generated log dump.
"""


def docs_plans() -> str:
    """Return the scaffold text for the docs plans documentation page."""
    return """---
subject: docs:plans
role: index
state: planned
relations: canonical_for: planned work documentation
---

# Plans Documentation

Status: planned.

Purpose: hold target designs, roadmap material, and planned work that are not yet
promoted repository truth.

See also: [Documentation Index](../README.md), [Governance Docs](../governance/README.md),
[ETHOS Governance](../governance/ethos.md), and
[Decision Records](../decisions/README.md).

Plans can guide work, but they must be promoted into source, tests, package
metadata, accepted decisions, canonical governance/reference docs, or evidence
before they justify runtime or retirement claims.
"""


def docs_history() -> str:
    """Return the scaffold text for the docs history documentation page."""
    return """---
subject: docs:history
role: index
state: canonical
relations: canonical_for: historical documentation
---

# History Documentation

Status: canonical.

Purpose: hold retired rationale, archival logs, and migration history.

See also: [Documentation Index](../README.md), [Governance Docs](../governance/README.md),
and [Reference Docs](../reference/README.md).

History preserves context; it does not override source, canonical governance/reference docs,
decisions, or evidence.
"""
