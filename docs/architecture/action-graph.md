---
subject: ethos:action-graph
role: concept
state: canonical
relations:
  canonical_for: deterministic planning
---

# Action Graph

`ethos plan` emits a deterministic action graph. Each action node declares
inputs, outputs, environment keys, command, policy, tool version, and cache key.

The graph borrows the hard mechanism from modern build systems: dependency
tracking, invalidation, cacheability, and affected planning. ETHOS owns the
governance semantics; runners such as local subprocess, Dagger, or hosted CI are
replaceable adapters.
