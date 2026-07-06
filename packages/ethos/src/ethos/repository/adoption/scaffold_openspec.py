"""OpenSpec scaffold text templates."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


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
routing metadata in `capability.toml`. Capability directory names are stable
product semantics, not package names. Proposal capability entries must name live
capability directories exactly; aliases are diagnostic only.
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
package = "ethos"
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
        "kernel": "Pure Kernel",
        "contracts": "Provider-neutral Contracts",
        "repository-governance": "Repository Lifecycle Governance",
        "adapters": "Provider Adapters",
        "command-plane": "Public Command Plane",
        "assistant-projections": "Assistant And Context Boundaries",
        "distribution": "Distribution Adapters",
        "quality": "Quality And Determinism",
        "proof-hosts": "Conformance And Parity Proof",
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
        "kernel": "pure kernel result and action graph semantics",
        "contracts": "provider-neutral repository contracts",
        "repository-governance": "repository lifecycle governance",
        "adapters": "provider and projection adapters",
        "command-plane": "public ETHOS command plane",
        "assistant-projections": "assistant and context projection boundaries",
        "distribution": "distribution and host package surfaces",
        "quality": "quality, determinism, docs profile, and proof policy",
        "proof-hosts": "conformance, fixture, and parity proof hosts",
    }
    profile_families = {
        "kernel": "kernel",
        "contracts": "contracts",
        "repository-governance": "repository-governance",
        "adapters": "adapters",
        "command-plane": "surfaces",
        "assistant-projections": "surfaces",
        "distribution": "surfaces",
        "quality": "quality",
        "proof-hosts": "proof",
    }
    owners = {
        "kernel": "ethos-core",
        "contracts": "ethos-core",
        "quality": "ethos-core",
    }
    scope = scopes[family]
    owner = owners.get(family, "ethos")
    return f'''family = "{profile_families[family]}"
primary_invariant = "The {family} capability keeps {scope} cohesive and provider-neutral."
routing_question = "Does this change alter {scope}?"
decision_axes = ["lifecycle", "surface", "authority"]
boundary_rules = [
  "Capability IDs name stable product semantics, not implementation package names.",
  "OpenSpec records are specification carriers, not truth owners.",
  "Provider or adopter-specific state remains in adapters, profiles, or evidence.",
]
aliases = []

[owner]
package = "{owner}"
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
