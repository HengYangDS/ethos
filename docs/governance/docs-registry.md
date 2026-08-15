---
subject: ethos:docs-registry
role: explanation
state: canonical
relations:
  canonical_for: documentation governance
---

# Docs Registry

Status: canonical.

Purpose: define how ETHOS turns documentation into mechanically checkable
knowledge sedimentation.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md),
and [Glossary](../reference/glossary.md).

ETHOS documentation is governed as sedimented knowledge, not as a loose page
pile. Every governed document declares Subject, Role, State, and Relation
metadata in front matter.

`ethos prove --gate docs-registry --json` is the reader-facing and machine
quality entrypoint.
Missing metadata is a required gap because agents need to distinguish canonical
truth, active workflow notes, planned material, experimental material, and
archived history before they act.

The registry lifecycle is:

```text
observe -> shape -> canonize -> project -> retire
```

Archive material may preserve old vocabulary. Canonical docs must lead with the
single `ethos ...` command plane.

Superseded documents live only as explicit `docs/history/` carriers. Current
architecture, governance, reference, start, and plan surfaces must not retain
redirect or locator pages for retired concepts; they link directly to the
historical carrier when historical context is necessary. Retirement removes
only the redundant current-surface carrier, never immutable OpenSpec archives
or historical evidence bytes.

## Portability Boundary

The registry owns portable document metadata, role/state vocabulary, taxonomy
extensions, visible sections, command examples, and plan discoverability. It
reads the documentation root declared by the adopter profile, defaulting to
`docs/`; it does not require ETHOS's physical directories.

ETHOS's own physical documentation shape is a product self-audit concern. It is
not an adopter contract and is not exposed as a second topology gate. An
adopter may organize its documentation by its native subject domains while
retaining the same metadata and authority semantics.
