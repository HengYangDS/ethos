---
subject: ethos:docs-registry
role: reference
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

`ethos quality docs --json` is the reader-facing quality entrypoint.
`ethos quality docs-registry --json` is the lower-level machine registry report.
Missing metadata is a required gap because agents need to distinguish canonical
truth, active workflow notes, planned material, experimental material, and
archived history before they act.

The registry lifecycle is:

```text
observe -> shape -> canonize -> project -> retire
```

Archive material may preserve old vocabulary. Canonical docs must lead with the
single `ethos ...` command plane.
