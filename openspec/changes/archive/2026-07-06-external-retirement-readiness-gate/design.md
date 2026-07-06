# Design

The retirement-readiness gate is a fleet/adopter inspection command:

```bash
ethos fleet retirement-readiness --target <repo> --json
```

It treats the target as a repository governed through `.ethos/profile.toml`.
The profile supplies backend state, binding roots, execution config root, and
forbidden product-core adopter roots. ETHOS product code stays in generic
repository vocabulary and does not create `adopters/<name>`, `profiles/<name>`,
or `tests/fixtures/adopters/<name>` as product ontology.

The verdict has four layers:

1. Profile and binding checks: `.ethos/profile.toml` exists, is valid, and binds
   `.config/` as execution/config root when declared.
2. Product-boundary checks: every profile-declared forbidden product root is
   absent from the ETHOS product repository.
3. Evidence checks: parity gaps are clean and shadow parity has no false
   negatives.
4. Lifecycle checks: external backend is default/retirement-ready, embedded
   backend is frozen fallback/reference, and final retirement remains a separate
   decision after rollback-window evidence.

This makes a non-ready adopter actionable: stale evidence, product-boundary
violation, external-default gap, embedded-freeze gap, and rollback-window gap are
separate required gaps instead of one ambiguous migration state.
