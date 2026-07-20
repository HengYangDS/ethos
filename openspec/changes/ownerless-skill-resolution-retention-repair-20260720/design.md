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
dbf17ff352e530e673366c9806a25c05331ddc95. The inverse must restore every
affected path to the e54b81d06273d562b5a97dff777dcdc50f113272 tree for that
range. No reset, force update, or protected-root edit is permitted.

### 2. Stable records owner

Resolve the configured accepted checkout from the current repository's
registered worktrees. New lane-resolution artifacts live under:

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
Explicit decision paths outside the canonical records root or supported legacy
root fail closed.

### 3. Legacy compatibility and retirement guard

Inventory and clear retain read-only compatibility with legacy
build/artifacts/lane-resolution records in the accepted checkout or current
caller worktree. A duplicate decision ID with conflicting records is a blocking
inventory conflict, never last-writer-wins.

Immediately before ordinary linked-lane removal, ETHOS scans the selected
worktree for legacy build/artifacts/lane-resolution/*/manifest.json. Presence
means retained recovery material still depends on that worktree, so retirement
blocks before worktree, ref, or lease mutation.

### 4. Honest partial-transition reporting

The preservation package and a schema-valid completion receipt payload are
prepared before destructive retirement. If final immutable receipt
materialization fails after the source transition, ETHOS reports a
partial-transition gap while leaving the stable decision and package
inspectable; it must not throw an unclassified exception or report success.

### 5. Lost-package reconciliation

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
Run focused Ruff and pytest, strict OpenSpec lifecycle, claims validation,
generic parity, default and full exact-HEAD proof, candidate land, accepted
closeout, and only then the bounded recovery-lane preserve-retire. Final
inventory must find and verify the new retained package after the recovery lane
is gone.
