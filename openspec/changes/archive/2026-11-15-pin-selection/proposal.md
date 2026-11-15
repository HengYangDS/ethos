# Proposal

## Why

This Change is row C2 of the 0.2.0 release-candidate order: the archived `rc-plan` design's Decision
2, Family 7, with Appendix C.2 item 2 as its done conditions. The release-candidate gate requires
"`github-pin` step 2 Changes 1 to 5", and its items R8(b) and R9 require that no unattested lock is
selected and that `CURRENT` never moves back without a receipt. The release-candidate scope approved
on 2026-11-14 (DR-0026) ships it in beta.11 with C1, C3, `release-identity` and `adopter-bump`.

Today every console selects itself: `hook install`, `lane start` and `adopt --select-runtime`
activate the invoking build, so a repository's runtime follows whichever console ran last, and a
lane that binds a successor or rolls back leaves no record. A cutover also holds its predecessor as
`ROLLBACK` without asking whether an install would admit it; the approved common-base design's
decision 4 gives C2 that proof.

## What Changes

- Without `--runtime`, hook activation and `adopt --select-runtime` read the exact GitHub pin and
  its lock entry from the accepted branch. They select the pinned release's install only when it is
  newer than `CURRENT`; otherwise `CURRENT` stays and the result names the state:
  `runtime_pin_behind_current`, `runtime_pin_unattested`, `runtime_pin_not_installed` or
  `runtime_selection_open`. Without a pin the invoking build is selected as before, with the
  advisory `runtime_pin_absent`. ETHOS installs and fetches nothing.
- `hook install` gains `--reason`. From a Work Lane, `hook install --runtime <R> --reason <text>`
  for a release other than the accepted pin writes a `successor` or `rollback` receipt under
  `<git-common>/ethos/receipts/runtime-selection/` before any effect. The receipt keeps `CURRENT` on
  R until the accepted pin changes or the lane retires.
- A cutover holds `ROLLBACK` only for a predecessor that an install of the root can admit. `status`
  reports a held rollback that no install can admit, with one repair.

Not Breaking: a repository whose accepted branch declares no exact GitHub pin behaves as before.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `runtime-activation`: ADDED `Runtime activation follows the accepted pin forward` and
  `A lane-bound selection receipt holds a departure`; MODIFIED
  `A rollback across a repaired declaration refuses until restored`.

## Impact

`src/ethos/adapters/repo/runtime/pin_selection.py` (new), the runtime selection, hook activation
and hook observation modules, the adoption adapter, the `hook install` request, the status
inspection's one call, their unit tests, `docs/architecture/local-state.md` and
`openspec/specs/runtime-activation/spec.md` through this Change's delta. It reads C1's
`release/pin.py` and adds no reader of its own. Out of scope: writing the pin at adoption (C3), the
adopter bump, the restore-then-rollback journey (B8) and a selector rollback in the product's own
repository.
