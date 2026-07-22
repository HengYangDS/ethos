# Design: T8 Adoption-Retirement Test-Matrix Compression

## Context

The primary adoption-retirement test module contains 30 passing tests and 731
`scc` code lines. Together with its existing fixture module, the scoped baseline
is 968 code lines, 506 unique lines, and 462 repeated lines. Repetition is
concentrated in repository setup, parity/shadow payloads, manifest mutations,
report invocation, and equivalent gap assertions.

The product implementation is outside this Change. The test surface must keep
the same public retirement states, gap vocabulary, effect boundaries, and CLI
contracts while becoming materially smaller.

## Decisions

1. **Use literal pytest case tables for finite partitions.** Each case carries
   only input mutation facts and exact expected public gaps/state. Domain-named
   ids preserve diagnostic locality. This is preferred over a custom DSL because
   the DSL would become another semantic owner.
2. **Reuse the existing fixture module.** Only inert repository construction,
   manifest text, and invocation envelopes may move there. Expected retirement
   classification remains literal in tests and never calls production helpers.
3. **Retain named effect tests.** Git tracking/reachability, CLI execution,
   generated-artifact drift, docs topology, and rollback evidence paths keep
   direct tests because their setup and failure boundaries are materially
   different.
4. **Measure after Ruff.** The cutover is admitted only when focused tests pass
   and formatter-clean scoped code/duplicate totals meet the numeric limits.

## Risks / Trade-offs

- **A table can hide semantics** → keep exact expected gaps and descriptive case
  ids; retain direct tests for effects.
- **A helper can become a parallel implementation** → helpers may construct
  literal files and call public APIs only; no classification or normalization.
- **Line reduction can weaken assertions** → preserve exact state, gap, check,
  and next-action assertions rather than replacing them with broad truthiness.
