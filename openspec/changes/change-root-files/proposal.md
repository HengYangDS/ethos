# Proposal

## Why

Prewrite refuses a selected Change's write to another active Change's files: a path inside another
Change's directory reports `openspec_change_path_mismatch`. The rule,
`prospective_change_scope_report` in `src/ethos/adapters/openspec/lifecycle/scope.py`, takes the
third segment of every path under `openspec/changes/` as a Change name. A file directly in
`openspec/changes/`, such as di-effect's `README.md` guide and its `template.md`, therefore reads as
a Change named `README.md`, and no selected Change can repair it.

- On 11-03 the di-effect Work Lane `serena-activation-ownership` repaired stale links in
  `openspec/changes/README.md`. With `ETHOS_CHANGE=tooling-core-runtime-convergence`, prewrite
  reported `openspec_change_path_mismatch` for that file; without a selection it reported, as it
  should, that eight active Changes were ambiguous.
- Every other ETHOS rule that maps a path to a Change requires a path inside a Change directory, of
  at least four segments: `artifact_path_change` and `preserved_incoming_change_paths` in
  `src/ethos/adapters/openspec/selection.py`, archived-reference repair, the documentation registry
  and the OpenSpec audit.

## What Changes

- The cross-Change rule refuses only paths inside another Change's directory.
- A file directly in `openspec/changes/` belongs to no Change. A selected Change writes it under its
  ordinary material scope and every other prewrite control.
- Without a selection, several active Changes stay ambiguous, as today.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: files directly in `openspec/changes/` belong to no Change.

## Impact

`prospective_change_scope_report` in `src/ethos/adapters/openspec/lifecycle/scope.py`, the path
admission tests and the changelog. Adopters that keep guides in `openspec/changes/` can repair them
from a selected Change; no other admission rule changes.
