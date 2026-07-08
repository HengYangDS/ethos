---
subject: ethos:adapter-lifecycle
role: explanation
state: canonical
relations:
  canonical_for: adapter lifecycle
---

# Adapter Lifecycle

Adapters begin as experimental projections. They become active only after they
prove stable input, output, failure, fallback, and retirement behavior.

Lifecycle:

```text
candidate -> experimental -> active -> deprecated -> retired
```

Retiring an adapter must not alter Subject, Commitment, Change, Evidence,
Chronicle, or Evolution semantics.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).
