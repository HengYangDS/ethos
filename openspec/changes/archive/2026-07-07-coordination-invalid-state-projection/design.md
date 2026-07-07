# Design

The fix reuses the existing invalid-state taxonomy and projection helper. No new
coordination ontology is introduced. The taxonomy addition is a prefix-level
normalization: a foreign Work Lane signal weakens the Change boundary, so it
belongs under `change_unbounded` with other Work Lane and coordination gaps.

The coordination package now exposes:

```text
required_gaps + advisory_gaps -> invalid_states
```

This keeps blocking semantics unchanged while letting humans, agents, schemas,
and future scorecards measure coordination small signals consistently.
