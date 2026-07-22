## Context

Lane-resolution preservation is not an ordinary rebuildable package artifact.
After a source ref and worktree are removed, its tracked patch, untracked
archive, and recovery bundle are the remaining local recovery material. Storing
those bytes below the invoking worktree gives the carrier that worktree's
lifecycle even though the retention decision requires a later, separately
authorized clear.

The repository already uses the configured accepted checkout as the local
coordination owner and its sibling <repo>-records directory for irreversible
recovery attempts and receipts. This change reuses that ownership pattern.

## Design

### 1. Correct the invalid accepted range

Create one signed forward-revert commit for
512ed20153761c66be85202f1ccf39bb9dd6b3a4 through
dbf17ff352e530e673366c9806a25c05331ddc95. The inverse removes that range's
invalid semantic delta while preserving later accepted changes to shared
specification and parity files. No reset, force update, or protected-root edit
is permitted.

### 2. Stable records owner

Read branch-role policy from the Git primary control root, then resolve the
configured accepted ref to a registered checkout whose HEAD matches that ref.
Mutable caller Work Lane bytes cannot redirect the owner. New lane-resolution
artifacts live under:

    <accepted-checkout-parent>/<accepted-checkout-name>-records/
      recovery/lane-resolution/
        decisions/
        receipts/
        clears/
        <decision-id>/

Single-worktree repositories use their accepted checkout in the same
deterministic rule. Artifacts remain non-authoritative local recovery records;
the tracked Chronicle and Claim continue to authorize transitions.

The CLI default decision path, preservation writer, package verifier, immutable
receipt writer, inventory, and clear transition must resolve this same owner.
New decision writes are admitted only below the canonical records root.
Explicit paths below legacy or unrelated roots fail closed with
`lane_resolution_decision_path_not_local_artifact`. Default paths combine a
branch digest and UUID; exclusive creation blocks an existing path with
`lane_resolution_decision_path_exists`. Decision identifiers use canonical
`lane-decision:<UUID>` form, and the final package realpath is rechecked below
the pinned records root before any write. A pre-existing package directory
blocks with `lane_resolution_preservation_package_exists`; preservation never
reuses or overwrites it.

### 3. Receipt reservation before effect

Before package creation or any destructive effect, apply reserves the
deterministic completion-receipt destination with a hidden, non-JSON sidecar in
the receipts directory. Reservation uses `O_CREAT|O_EXCL`, so two conforming
writers cannot both proceed. An existing final receipt or sidecar blocks with
`lane_resolution_receipt_path_exists` before package, ref, or worktree mutation.

Pre-effect failure and successful final receipt materialization release the
sidecar. If the destructive effect completes but the final no-clobber receipt
write fails, the sidecar remains as fail-closed reconciliation state and the
command reports a partial transition. The receipt writer independently repeats
path-safety and no-clobber checks; reservation does not weaken immutable final
record semantics.

### 4. Legacy compatibility and retirement guard

Inventory, verification, and clear retain read-only compatibility with legacy
build/artifacts/lane-resolution records across registered worktrees. A duplicate
decision ID with conflicting records blocks inventory and clear with
`lane_resolution_decision_record_conflict`; scan order is never authoritative.
Byte-identical package copies remain ambiguous for clear and block with
`lane_resolution_clear_package_ambiguous`. Inventory binds the actual durable
manifest digest to the immutable receipt and blocks mismatch with
`lane_resolution_manifest_receipt_mismatch`; verification rereads that durable
manifest instead of accepting stale caller memory.

Package, manifest, receipt, and clear-record paths reject symlink components.
Inventory and clear report `lane_resolution_package_path_unsafe` or
`lane_resolution_record_path_unsafe`; completion-receipt safety is checked before
destructive effect and rechecked during atomic materialization. Clear rechecks
the selected package and manifest immediately before removal.

Immediately before ordinary linked-lane removal, ETHOS scans the selected
worktree for legacy build/artifacts/lane-resolution/*/manifest.json. Presence
means retained recovery material still depends on that worktree, so retirement
blocks with `lane_resolution_legacy_retention_present` before worktree, ref, or
lease mutation.

### 5. Honest partial-transition reporting

The preservation package and a schema-valid completion receipt payload are
prepared before destructive retirement. If final immutable receipt
materialization fails after the source transition, ETHOS reports `ok=false`,
`state=partial_transition`, and
`lane_resolution_receipt_write_failed_after_effect` while leaving the stable
decision and package inspectable; it must not throw an unclassified exception or
report success.

The accepted control root and records root are pinned before a destructive
effect. Receipt materialization therefore remains possible even when the command
was invoked from the exact worktree that the effect removes.

### 6. Lost-package reconciliation

The original tracked patch is available as 9,673 exact bytes with SHA-256
26fdae9bbaf9ce6460bca5a5bbbcf196d42e5d35af0fdfb55e7898a654fee07b.
The source commit 87911a89faeb01d97a29afce1c24e0fc5ed94f2a remains
reachable. After this change is archived, proven, landed, and accepted, a new
ownerless recovery lane may be created from that source commit, the patch
applied, and the resulting git diff --binary HEAD -- digest rechecked. A new
Chronicle-bound lane_resolution/preserve-retire creates a new package and
receipt in the records owner. The unavailable original bundle and deleted old
receipt remain recorded as irreversible evidence loss.

## Alternatives

- Only block carrier retirement: rejected because it turns retained packages
  into permanent worktree residue and leaves inventory bound to the caller.
- Only route to accepted build/artifacts: rejected as the terminal design
  because that topology is declared rebuildable local output while recovery
  packages are not reproducible after source deletion.
- Silently migrate every legacy package: rejected because foreign worktrees
  and conflicting decision IDs require independent ownership and evidence.

## Proof Strategy

Use red-green tests for cross-worktree artifact ownership, legacy inventory,
duplicate conflict, receipt-write partial transition, and retirement blocking.
Run focused Ruff and pytest, strict OpenSpec lifecycle, claims validation, and
docs validation before the official archive transition. Then refresh generic
parity, run default and full exact-HEAD proof on the archived HEAD, land to the
candidate, complete accepted closeout, and only then execute the bounded
recovery-lane preserve-retire. Final inventory must find and verify the new
retained package after the recovery lane is gone.
