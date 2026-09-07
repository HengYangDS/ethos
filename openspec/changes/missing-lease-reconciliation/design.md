## Context

The Product Design Contract requires reacquisition from current facts rather
than historical Lease resurrection. The historical source-policy lane is a
registered `work/*` checkout with three dirty files and no Lease. Its prewrite
decision correctly blocks; start requires the candidate HEAD, while takeover
requires an existing exact Lease generation. None supplies the missing
coordination transition.

## Goals / Non-Goals

Provide one public, bounded missing-to-owned coordination transition, including
dirty linked Work Lanes. Preserve every Git ref, index entry, tracked byte, and
untracked byte. A resulting Lease does not replace OpenSpec or prewrite.

Do not make absence of a Lease authorize content deletion, manufacture previous
ownership, introduce a second workflow database, or broaden takeover.

## Decisions

1. Add `lane lease reacquire` to the existing Lease owner. A dry-run derives an
   exact apply command from fresh coordinates. Apply requires the same actor,
   explicit authorization, expected HEAD, and a digest binding the index, working
   content, and proposed four-field Lease including its bounded expiry. Callers
   do not assemble canonical bytes or edit SQLite.
2. Observe only a registered Work Lane using policy and repository identity from
   the surviving accepted control root. Reject detached, protected, ambiguous,
   locked, missing, and foreign-common-directory targets. A valid or expired
   existing Lease is not a missing Lease and cannot be overwritten.
3. Reuse the SQLite insertion owner under its immediate transaction. Recheck
   the Git/content snapshot around insertion; drift rolls back the insertion.
   Keep only lane, holder, generation, and expiry in the Lease. Exact operation
   bindings belong to the request and native-effect Attestation, not the row.
4. Repeating the operation recognizes only its exact four-field Lease postimage,
   not merely the same holder. It reuses existing matching evidence and does not
   increment generation or alter content. If evidence publication fails after
   the Lease commits, report that partial boundary and permit exact postimage
   observation; do not claim the retry witnessed the original missing state.
5. Missing-Lease guidance points to derivation, not start. Coordination recovery
   does not claim OpenSpec acceptance, proof, integration, or permission to edit.
6. The existing Lease namespace separates three complete operations: acquiring
   missing coordination, changing an existing relation, and accepted-authorized
   takeover. Each hides its own admission and recovery; the CLI only transports
   inputs. The former mixed module is removed without a forwarding facade.
   Reference closure distinguishes its deleted file from the retained Python
   namespace using current source owners. Imports of replacement submodules are
   valid; references to the deleted physical path or genuinely retired import
   identities remain invalid. No name-specific exception is introduced.

## Risks / Trade-offs

External processes can mutate Git content without respecting the coordination
transaction. Double observation detects changes at this boundary; a later edit
still requires fresh prewrite and effect-time admission. A byte snapshot is
deliberately not evidence of semantic absorption.

The source-policy lane's product behavior already exists, but its exact missing
distribution allowlist assertion does not. Preserve that small regression in
the current owner rather than transplanting historical policy or all 404 lines.

## Migration Plan

Accept the package implementation before using it on historical lanes. Derive
each target from current facts, retain its overlay, reacquire coordination, and
separately admit any content reconciliation. The existing terminal route owns
remaining lane dispositions and post-archive closeout, not this task file.
