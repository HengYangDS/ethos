---
subject: ethos:runner-mutation
role: reference
state: canonical
relations:
  canonical_for: workspace execution boundary
---

# Runner And Mutation Boundary

ETHOS separates planning from execution. The kernel emits an action graph; the
workspace layer chooses a runner.

Initial runners are deliberately small:

- `DryRunRunner` records the action without side effects.
- `LocalSubprocessRunner` executes a node in a chosen repository root.
- Future Dagger, hosted CI, Temporal, or remote agent runners must consume the
  same action graph contract.

Tracked mutation is gated by a mutation decision. `ethos land --apply` and
`ethos publish --apply` require explicit authorization and an expected HEAD.
Without both, the command returns `authorization_required` or
`expect_head_required` instead of mutating.

This keeps break-glass paths explicit and makes dry-run planning safe by
default.
