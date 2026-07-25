## Context

The accepted reconciliation carrier authorized a transient preservation bridge
for three exact clean ownerless lanes after direct retire reached a correct WCP
no-effect boundary. Native effects have now removed all three exact branches and
worktrees while retaining content-addressed packages with valid bundles and
empty tracked/index patches.

## Decisions

### 1. Treat the packages as transient recovery bridges

The packages preserve recoverability of the native effect, not product truth.
Their exact heads, semantic outcomes, decision records, completion receipts, and
manifests are already bound. No package contributes a missing current
capability.

### 2. Bind all three exact manifests in one successor, clear individually

One successor carrier records the complete three-item set because all packages
share one accepted authority and one effect boundary. It does not authorize a
batch command: each native clear is a separate exact decision-and-manifest CAS
transition with its own dry-run, apply, and clear receipt.

### 3. Preserve durable evidence

Clear removes only the selected package. The original decision, completion
receipt, and later clear receipt remain immutable. A mismatch, duplicate
package, unsafe path, missing receipt, or inventory conflict blocks that one
transition and leaves every package intact.

## Proof Strategy

Verify inventory, all three manifests and bundle digests, empty patches, absent
source refs and worktrees, strict OpenSpec, Claim digests, generic parity, and
executed exact-HEAD proof. Archive, land, and accepted-close before any clear;
then clear one package at a time and verify final inventory before retiring this
owned carrier.
