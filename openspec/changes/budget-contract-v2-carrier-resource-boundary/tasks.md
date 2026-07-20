## 1. Metric Resource Contract RED

- [ ] 1.1 Add failing contract tests for required v3 execution fields, strict
  positive byte ceilings, no unknown/path override fields, provider-wide
  consistency, resource helper admission, and digest propagation.
- [ ] 1.2 Run the focused kernel tests and retain the expected missing-field,
  wire-version, helper, schema, and provider-consistency failures.

## 2. Reader And Native Boundary RED

- [ ] 2.1 Add failing tests for limit-minus-one, exact-limit, pre-read
  limit-plus-one rejection, growth during reading, stable public gaps, native
  rejection before startup/decode/parser calls, forged signatures, and complete
  snapshot rejection.
- [ ] 2.2 Run the focused adapter tests and retain failures caused by the absent
  pre-read and native resource boundary.

## 3. Metric Contract And Provider Signature GREEN

- [ ] 3.1 Implement MetricContract v3 execution fields, provider consistency,
  the resolved resource-contract helper, and schema generation.
- [ ] 3.2 Add exact provider execution descriptors, advance the descriptor wire
  version, regenerate every grammar digest, and update all policy atoms without
  path overrides or defaults.
- [ ] 3.3 Verify that resource fields change registry/resolved/native/carrier/
  snapshot identity but do not change admitted metric values or vector digest.

## 4. Descriptor Reader And Native GREEN

- [ ] 4.1 Resolve the complete resource contract before opening bytes, reject a
  pre-read oversize object, bound reads to `limit + 1`, and preserve descriptor
  cleanup and object-stability checks.
- [ ] 4.2 Recheck direct bytes before startup conformance, decode, AST, or parser
  dispatch and return no partial result.
- [ ] 4.3 Verify the full current inventory has no new oversize gap and preserves
  the one existing deterministic YAML graph-safety gap.

## 5. Quality And Governance Closeout

- [ ] 5.1 Run focused statement/branch coverage, native and v1 regressions,
  Python/config/schema/dependency/module-layout/code-size gates, and strict
  OpenSpec/claim validation without raising a ratchet or threshold.
- [ ] 5.2 Complete independent security, contract, and simplicity review; if the
  byte ceiling is rejected, keep C1 open and implement admitted isolation.
- [ ] 5.3 Bind final evidence and promotion targets, refresh parity, run exact-HEAD
  default/full proof, archive, archive-HEAD proof, candidate land, accepted-root
  closeout, local publish readiness, and owned-Lane retirement as separate
  transitions.
