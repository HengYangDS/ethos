"""Adoption decision-record scaffold generators."""

from __future__ import annotations


def decision_records() -> str:
    """Return the scaffold text for the decision records decision record."""
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


def decision_index() -> str:
    """Return the scaffold text for the decision index decision record."""
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


def decision_dependency_map() -> str:
    """Return the scaffold text for the decision dependency map decision record."""
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


def decision_code_links() -> str:
    """Return the scaffold text for the decision code links decision record."""
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


def decisions_accepted() -> str:
    """Return the scaffold text for the decisions accepted decision record."""
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


def decisions_superseded() -> str:
    """Return the scaffold text for the decisions superseded decision record."""
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


def decisions_templates() -> str:
    """Return the scaffold text for the decisions templates decision record."""
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


def decision_record_template() -> str:
    """Return the scaffold text for the decision record template decision record."""
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
