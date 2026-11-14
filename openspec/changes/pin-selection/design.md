# Design

## Context

See the [proposal](proposal.md). Line references are to `23538df6b`.

- `install_hook_launchers` (`src/ethos/adapters/repo/hook/activation.py:62`) is the one activation
  behind `hook install`, `lane start` and the candidate bootstrap, and `adopt --select-runtime`
  selects through `src/ethos/adapters/repo/adoption.py:177-231`. Both select the invoking build
  unless `--runtime` names an installed one; neither reads the repository's own declaration.
- A named runtime is probed against the root's declaration first (`hook/rollback.py:47-57`), then
  admitted by build, scope and exact wheel and copied into the host store
  (`runtime/materialization/effect.py:74-86`).
- A cutover pins its predecessor into the host store and writes `ROLLBACK` (`activation.py:222-227`,
  `:373-396`) without asking whether an install could admit it. Where the accepted source names the
  expected build (`runtime/authority.py:82-93`), an install admits that build alone
  (`runtime/selection.py:336-342`), so `hook install --runtime` refuses the held rollback with
  `hook_runtime_manifest_invalid`.
- C1's `src/ethos/repository/release/pin.py` reads the pin, its lock entries and each release's
  class from text. This Change calls `PIN_KEY`, `ATTESTED_PROVENANCE`, `declared_pin`, `lock_entry`
  and `release_class`, and adds no reader.

## Goals / Non-Goals

Goals:

- A transition without `--runtime` follows the accepted branch's pin, forward only, and names every
  state in which it leaves `CURRENT` in place.
- A lane's departure from the pin is recorded before it takes effect, and lasts no longer than the
  pin or the lane.
- `ROLLBACK` names only a runtime that an install of the root can admit, and `status` says when it
  no longer does.

Non-Goals:

- Writing the pin at adoption (C3), the adopter bump, and the restore-then-rollback journey (B8).
- Installing or fetching a release: Mise owns both.
- A selector rollback in the product's own repository, where the accepted source names the build.
- The top-level `next` of the `status` result, which other Changes of this batch route. A passing
  `hook install` that leaves the accepted pin unselected names the pin's own action as its next
  action; the pin's state stays under `runtime_pin` and the rollback's under
  `hook_runtime.rollback`.

## Decisions

1. **One decision, two callers.** `follow_accepted_pin` in
   `src/ethos/adapters/repo/runtime/pin_selection.py` returns the install to select, the selection
   to keep, or neither, in which case the invoking build is selected as before. Hook activation and
   the adoption adapter both call it and pass an install on as the existing `installed_runtime`, so
   the scope check, the declaration preflight and the host-store copy stay. A kept selection is
   activated as it stands, neither built nor pinned. A configuration that never names the pin is
   read no further, so an unpinned repository behaves as before whatever else its file holds.
2. **Forward only.** With a selection in place: an open receipt keeps it (`runtime_selection_open`),
   an older pin keeps it (`runtime_pin_behind_current`, whose next action is the receipted install),
   and the pinned release itself keeps it. Only a newer pin is judged and selected. Order is the
   build's own version order, in which a development build precedes the release of its version, so
   a lane-built runtime gives way to the pinned release of the same version. The alternative,
   moving back to the pin when a `successor` receipt closes, is the implicit move to an older
   release that the release-candidate design forbids.
3. **A pin that cannot be selected moves nothing.** An unattested lock entry, an uninstalled release
   and a pin that its reader refuses all keep `CURRENT` and name the state; with nothing selected
   they refuse by the same name, and the next action names the explicit `hook install --runtime`
   that selects a runtime first. The archived design says "refuse" for the unattested case; this
   Change refuses to select it but does not block the transition, because `lane start` runs the same
   transition and a lane is the only place where the pin can be repaired.
4. **The lock is a precondition, read last.** The platform's entry is read only where the
   transition would select the pinned bytes. Outside the `checksum` class it must record
   `github-attestations`; a `checksum` release needs neither that nor the setting. The lock's field
   proves nothing by itself, as C1 states.
5. **Mise is asked, never told.** `mise where <key>@<version>` runs through the existing isolated
   runner, offline and in safe mode with an empty configuration, and the install's one
   `runtime/<16 hex>` generation is the runtime. Any other answer reads as not installed, with
   `mise install --locked` as the next action.
6. **The receipt.** `hook install --runtime <R>` for a release other than the accepted pin needs
   `--reason` and a Work Lane root, or refuses with `runtime_selection_receipt_required`. After the
   declaration preflight and before materialization it writes
   `<git-common>/ethos/receipts/runtime-selection/<pin>.json` with the kind (`successor` when R is
   newer, `rollback` when older), the pin, the release, the runtime's digest, the lane and the
   reason, and returns what it reads back. A receipt holds only while its pin is the accepted one,
   its lane's ref exists and `CURRENT` is the runtime it names; only a transition deletes a closed
   one, so a preview stays read-only. Git state closes it, so lane retirement needs no new step.
   Selecting the pinned release, or any release where no pin is declared, is no departure.
7. **A rollback is proved before it is held.** `rollback_gap` in `runtime/selection.py`, beside the
   selector readers, names why no install of a root can admit a runtime: its manifest is gone or
   unreadable, or the root's accepted source requires one exact build and the runtime is another.
   A cutover neither pins nor holds such a predecessor and reports `rollback_supply` as `unrunnable`
   with the gap the install would name; a predecessor that it does pin is validated by the pin,
   payload and wheel. `status` runs the same proof on the held selector and reports an unrunnable
   one with that gap and one next action: the CURRENT console's `hook install`, which releases the
   selector and reports `rollback_released`. The proof reads one manifest. Validating the held
   payload on every `status` was rejected: on one shipped runtime of 13,573 files it took 5.9
   seconds cold and 0.7 to 0.9 seconds with the inventory memo. The declaration probe stays with
   the install, because a lane can still restore the declaration.

## Risks / Trade-offs

- **The product's own repository holds no rollback.** There the accepted source names the one build
  an install admits, so every predecessor of another build is unrunnable: no copy enters the host
  store, the local generation is reclaimed as before, and `status` names no rollback. That is what
  an install does there today; a working selector rollback needs its own design.
- **The declaration preflight still refuses a forward move.** A pinned release that refuses the
  accepted tree's publication declaration, or whose probe cannot answer, refuses the transition,
  `lane start` included, under the preflight's own gap. A lane that already exists repairs the
  declaration and selects the release with `hook install --runtime`; without one, uninstalling the
  pinned release makes the transition keep `CURRENT`. Keeping `CURRENT` there too, as decision 3
  does for the pin's own states, is left to review.
- **An older console that follows the pin forward writes its own launchers.** Activation refuses
  and restores when the selected release declares other launcher bytes, and the pinned console's
  `hook install` then moves the selection. The launcher declaration is unchanged from beta.2
  through this Change's base.
- **Mise's view decides "installed".** A release that another Mise data directory holds, or a host
  without Mise on `PATH`, reads as `runtime_pin_not_installed`. The install's layout is the one C1
  proves in its hosted journey.
- **`status` reads the held rollback's manifest only.** A payload or wheel damaged after the pin is
  found by the install, which refuses by name.
- **A lane's name can reopen a receipt** when a new lane takes a retired lane's name before any
  transition ran; lane names carry a date and a slug. One receipt exists per accepted pin, so a
  later departure replaces an earlier one.
- **In a pinned repository the rollback that `status` names needs a reason.** Its command is
  refused with `runtime_selection_receipt_required`, whose next action names the receipted form.
- **Names.** The archived design's restore-then-rollback text says `runtime_rollback_open`; this
  Change reports `runtime_selection_open` for both receipt kinds, and B8 reads that name.
- **Size.** About 275 product and 440 test line-equivalents against an estimate of 185 each, made
  before the rollback proof joined this Change. The proof is about 55 and 70 of them; the tests of
  the pin and the receipt are about 370, of which one journey through real activation is 82.
