---
subject: ethos:adapter-lifecycle
role: reference
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
