# Proposal

## Why

An agent that follows `next` from `ethos hook install` can run the same installation forever. At
`23538df6b` three results name the request that produced them:

- An installation whose activation holds while reclamation is deferred reports `block`,
  `installed_cleanup_deferred` and `ethos hook install --json`, without a root
  (`src/ethos/adapters/repo/hook/activation.py:134-136`). Residue that no retry removes, such as a
  legacy locator that is a directory, repeats it on every run.
- An installation that refuses for any reason other than installed supply or its state schema
  reports `ethos hook install --root <root> --json`, the refused request
  (`src/ethos/application/hook/installation.py:137-148`).
- An authorized reset that met a reset gap would name the authorized reset again; no adapter path
  raises that today, and the builder alone allowed it.

The command-plane specification requires the second case: `Installation cannot establish
convergence` ends with "`next_action` is the complete root-bound `ethos hook install` command"
(`openspec/specs/command-plane/spec.md:450-454`).

This Change is row A8 of the release-candidate plan
(`openspec/changes/archive/2026-11-07-rc-plan/design.md`): Decision 2 names it in Family 5
(`:115-116`), Appendix A.3 ends with "A `next` equal to its own command is a loop" (`:288-289`),
A.9 names Breaking (4) (`:368`), and A.11 lists it as item 8, "ending the `hook install` self-loop"
(`:397-398`). The release-candidate gate's item R1 requires it by name ("the `hook install`
self-loop"). It is budget B3, "zero self-loops and blocked steps", of the product-form plan
(`openspec/changes/archive/2026-11-12-product-form-plan/design.md:82`, decision 5). In the
release-candidate scope that the owner approved on 2026-11-14 it belongs to the first weekly batch,
beta.11 of 2026-11-21.

## What Changes

- A deferred reclamation and a refusal continue to `ethos status --root <root> --json`, whose
  hook-runtime inspection already owns the one repair command. The verdict, the gap
  `hook_runtime_cleanup_deferred`, the state and the exit stay as they are.
- A state that only a reset repairs still continues to the authorized reset, unless that request
  just ran; a refusal for installed supply keeps its instruction and its user decision.
- Hook activation returns facts only: it no longer writes a continuation into its binding.
- One table-driven guard, beside the catalog's static rules, refuses an installation result whose
  `next` selects the producing operation with the same root and an equal request.
- The command-plane reference and the hook rules say the same.

Not in this Change: Breaking (4) of the plan, "`hook install` deletes nothing, reclamation moving
to `hook retire-supply`". It does not hold at `23538df6b`, and the move is several times this
Change's size; the design records the evidence and the estimate for the owner's decision.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `command-plane`: MODIFIED requirement `Hook installation reports repository-family convergence`.
- `runtime-activation`: MODIFIED requirement `Runtime activation includes Git-common state`.

## Impact

`src/ethos/application/hook/installation.py`, `src/ethos/adapters/repo/hook/activation.py`, their
unit tests, `tests/unit/kernel/test_operation_catalog.py`, `docs/reference/command-plane.md`,
`rules/hooks.md`, `CHANGELOG.md`, and the two specifications through this Change's deltas. A reader
that reran the installation on its old continuation now runs `ethos status` first.
