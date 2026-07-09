"""Adoption documentation-page scaffold generators."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos_core.contracts.docs.topology import ROLE_VALUES
from ethos_core.contracts.docs.topology import STATE_VALUES

if TYPE_CHECKING:
    from pathlib import Path


def docs_taxonomy() -> str:
    """Return the starter docs taxonomy for an adopted repository.

    Seeds the inherited role/state vocabulary and the extension-root role law
    for the roots this scaffold creates. Adopters extend [extension_roots] with
    their own docs roots; they never need to edit ETHOS core.
    """
    roles = "".join(f'  "{role}",\n' for role in ROLE_VALUES)
    states = ", ".join(f'"{state}"' for state in STATE_VALUES)
    return (
        "[meta]\n"
        "version = 1\n"
        'owner = "adopter"\n'
        "\n"
        "[semantic_axes]\n"
        'required = ["subject", "role", "state", "relations"]\n'
        "\n"
        "[states]\n"
        f"allowed = [{states}]\n"
        "\n"
        "# Document roles name a document's function; kernel roles are inherited\n"
        "# from ETHOS and always valid. Add repo-specific roles here as needed.\n"
        "[roles]\n"
        f"allowed = [\n{roles}]\n"
        "\n"
        "# Map each product/adopter docs root to the roles it may hold. Kernel\n"
        "# roots (decisions/, evidence/, history/, reference/) are bound by the\n"
        "# ETHOS contract; declare your own extension roots below.\n"
        "[extension_roots]\n"
        '"docs/governance" = ["policy", "explanation", "ledger", "index"]\n'
        '"docs/start" = ["how-to", "index"]\n'
    )


def docs_index(root: Path) -> str:
    """Return the scaffold text for the docs index documentation page."""
    return f"""---
subject: docs:index
role: index
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
role: how-to
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

Purpose: route decisions, evidence, references, and history through the common
ETHOS-governed documentation topology.

See also: [ETHOS Product Index](index.md), [Quickstart](start/quickstart.md),
[ETHOS Governance](governance/ethos.md), [Decision Records](decisions/README.md),
[Evidence Docs](evidence/README.md), and [Reference Docs](reference/README.md).

## Common Kernel

| Lane | Owns |
| --- | --- |
| `decisions/` | Durable rulings with explicit scope and revisit triggers. |
| `evidence/` | Dated proof, manifests, smoke notes, and closeout records. |
| `reference/` | Stable vocabulary, boundaries, and governance references. |
| `history/` | Retired rationale and archival logs. |

Truth state is declared with explicit metadata such as `state: canonical`,
`state: active`, `state: planned`, `state: experimental`, `state: superseded`,
or `state: archived`. Do not use `current` or `future` as state values, and do
not encode them as path topology. Optional extension roots such as `docs/start/`,
`docs/governance/`, or repository-specific domain docs may exist for local UX,
but they are not required truth lanes.

Required kernel paths include `docs/decisions/README.md`,
`docs/evidence/README.md`, `docs/history/README.md`, and
`docs/reference/README.md`.
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

See also: [Documentation Index](../README.md) and [ETHOS Governance](../governance/ethos.md).

Reference docs explain terms and boundaries; runtime truth still comes from
source, tests, governed docs, and evidence.
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

See also: [Documentation Index](../README.md) and [Decision Records](../decisions/README.md).

Evidence supports claims; it is not the current API or a generated log dump.
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

See also: [Documentation Index](../README.md) and [Reference Docs](../reference/README.md).

History preserves context; it does not override source, governed docs, decisions, or evidence.
"""
