## 1. Hook Admission Runtime

- [x] 1.1 Add failing tests for pre-tool, pre-run, context, and post-write hook
  admission behavior.
- [x] 1.2 Implement the hook admission adapter around `prewrite_guard` and
  workspace status.
- [x] 1.3 Add CLI contract tests and expose `ethos hook admit --json`.

## 2. Governance Surfaces

- [x] 2.1 Add OpenSpec deltas for adapters, CLI, contracts, and repository
  campaign closeout state.
- [x] 2.2 Update command registry and command-plane docs for the maintainer hook
  surface.
- [x] 2.3 Update the campaign manifest to close the archive lane, activate this
  lane, and expose strict serial lane topology.

## 3. Evidence And Closeout

- [x] 3.1 Add claim and dated evidence for hooked write admission.
- [x] 3.2 Run focused tests, full tests, Ruff, schema validation, OpenSpec
  strict validation, lifecycle review, report, proof, and build.
- [x] 3.3 Land, accepted-root closeout, and retire this Work Lane before
  starting the next campaign step.
