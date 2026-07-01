## Why

The terminal governance redesign needs a repository-native planning carrier
before more implementation work proceeds. The previous accepted-root and
wrong-root write incidents show that advisory rules and manual prewrite calls
are insufficient when mutation tools can bypass repository context and OpenSpec
planning.

## What Changes

- Capture the terminal ETHOS product design as a tracked architecture target,
  not as chat-only rationale.
- Add a thin `AGENTS.md` entrypoint that forwards to canonical docs, rules, and
  skills instead of carrying detailed operating semantics.
- Introduce first-pass `rules/` and canonical `skills/` source surfaces for the
  target design without claiming full terminal implementation.
- Add hook and guard design for context refresh, pre-tool write admission,
  pre-run command risk checks, post-write fuse behavior, Git fallback hooks,
  and CI/release proof hooks.
- Add the failure-frontloading principle: repeated late failures move upstream
  from incident to diagnosis, rule, hook, scaffold/template, then schema/default.
- Add documentation progressive disclosure so agents load small entrypoints
  first and only expand into deeper references when the task requires it.
- Record that OpenSpec planning must precede non-trivial tracked design,
  rules, skill-system, hook, and product-shape changes.
- Keep this lane scoped to design, planning, and guard-hardening mechanism
  definition; it does not implement the terminal package collapse, complete
  projection generator, full hook runtime, or full scaffold system.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `ethos-repository`: Clarifies repository-governance obligations for
  OpenSpec-first planning, thin agent entrypoints, Work Lane write admission,
  hook placement, failure-frontloading, and terminal governance design.
- `ethos-assistants`: Clarifies assistant and skill surfaces as progressively
  disclosed projections over repository truth, not independent truth stores.
- `ethos-contracts`: Clarifies contract requirements for context-bound mutation
  admission, source-digested projections, and format/carrier boundaries.

## Impact

- Affected files: `AGENTS.md`, `docs/architecture/terminal-governance-product-design.md`,
  `docs/index.md`, `rules/`, `skills/`, and this OpenSpec change.
- No runtime CLI, MCP, SDK, package, scaffold, hook, or projection-generator
  implementation is delivered by this change.
- The change creates design and task constraints for later implementation lanes
  to close the prewrite bypass and OpenSpec bypass as product bugs.
