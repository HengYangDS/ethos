---
subject: ethos:local-state
role: explanation
state: canonical
relations:
  canonical_for: ignored runtime state
---

# Local State

ETHOS stores host-local runtime state in `.ethos/state/state.sqlite`. The
directory is ignored except for `.ethos/state/.gitignore`. Tool runtime caches
live under ignored `build/runtime/tool-cache/`, not under `.config/`, because
configuration policy and runtime working state are different subjects.

SQLite records coordination and replay aids. It does not pre-create
speculative cache stores; action cache keys stay in action-graph contracts
until a concrete runtime cache earns its own owner and lifecycle.

- `leases`

No generic event, session, gate-run, action-run, or evidence-index table is
created speculatively. Durable Chronicle truth remains repository evidence,
not an ignored SQLite event stream. The `.ethos/state` SQLite coordination store
can be deleted and rebuilt without changing repository history.

The state owner currently records schema version 2. Initialization performs
ordered migrations in one SQLite transaction. Version 2 removes the retired
`cache_entries` table only when that table is empty; a non-empty table fails
closed and leaves the prior schema version recorded. Reopening a version-2
database is idempotent and does not rewrite active coordination rows.

Work Lane leases are local coordination facts recorded by lane-start flows. They
support ownership, handoff, and closeout ordering checks, but they do not replace
Git history, OpenSpec records, claims, evidence, or Chronicle judgments.
Productized leases identify the concrete acting holder, not merely a provider
class. Current prewrite and apply-mode admission are enforced by checkout role,
editor-root binding, HEAD checks, and active lease holder binding.

## Stable Recovery Records

Non-rebuildable lane-resolution recovery material is not stored in a disposable
Work Lane build tree. New decisions, preservation packages, immutable receipts,
and bounded clear records live below the configured accepted checkout's sibling
owner:

```text
<accepted-checkout-parent>/<accepted-checkout-name>-records/
  recovery/lane-resolution/
```

These records are ignored host-local evidence, not repository authority. The
tracked Chronicle and Claim still authorize every transition. Unlike runtime
caches or SQLite coordination, however, a preservation bundle and patch may be
the only remaining recovery material after source and carrier retirement, so
they are not assumed rebuildable and require an evidence-bound clear. Inventory,
verification, and clear retain read-only compatibility with predecessor per-worktree
`build/artifacts/lane-resolution/` records; ordinary retirement blocks while a
selected worktree still owns a retained predecessor manifest.

The Git primary control root owns the branch-role policy used to locate the
configured accepted checkout, so mutable caller Work Lane bytes cannot redirect
new records. Decisions are immutable, uniquely named, and created without
clobbering. Preservation verification rereads the durable manifest and binds it
to the immutable receipt before inventory or clear can report a consistent
retained transition.

Package, manifest, receipt, and clear-record paths are checked lexically against
the pinned owner and reject symlink components. Existing package directories are
never reused, and clear rechecks the package and manifest immediately before
removal.

Before any destructive lane-resolution effect, ETHOS reserves the deterministic
completion-receipt destination with a hidden, non-JSON sidecar created through
exclusive filesystem creation. An existing final receipt or reservation blocks
with `lane_resolution_receipt_path_exists` before a preservation package, branch
ref, or worktree is mutated. Pre-effect failure and successful receipt
materialization release the reservation; a receipt failure after the effect
retains it as fail-closed reconciliation state. Final receipt writing still uses
an independent no-clobber and no-symlink check.

## Explicit Maintenance

`ethos doctor` remains read-only by default. An operator can request a
maintenance inventory with an absolute archive root outside the repository and
an explicit observation time:

```bash
ethos doctor --maintenance \
  --archive-root /absolute/operator/archive \
  --observed-at 2026-07-19T00:00:00+00:00 --json
```

The inventory lists the SQLite migration state, lease and proof deletion
candidates, retained identities and reasons, and recovery-snapshot entries. It
also emits an `inventory_digest`. Applying the plan requires that exact digest
and an irreversible-action confirmation:

```bash
ethos doctor --apply-maintenance \
  --archive-root /absolute/operator/archive \
  --observed-at 2026-07-19T00:00:00+00:00 \
  --expect-inventory-digest <sha256> \
  --confirm-irreversible --json
```

Apply re-observes the inventory and rejects drift. Before deletion it archives
the database, proof records, and complete recovery snapshot tree; binds entry,
manifest, and archive digests; extract-tests the archive; and verifies every Git
bundle against the repository. A replay of a verified receipt is idempotent.

Lease pruning is conservative: a row must match the current lease contract, be
expired, absent from branch refs and linked worktrees, and have no existing
recorded path. Malformed,
ambiguous, active, or observable leases remain. Proof pruning retains current
HEAD, every ref-reachable commit, every linked-worktree HEAD, and every live
lease expected HEAD; malformed proof records are reported rather than deleted.
Maintenance output is ignored operator evidence and does not mint repository
authority.

## Adopted Repository Control Roots

When external ETHOS inspects an adopted repository from a linked Work Lane, the
accepted-root checkout remains the local coordination control root. ETHOS may
read the adopter's ignored `.cache/local-state/worktree/leases.json` projection
from that accepted root to preserve existing embedded Work Lane leases during
shadow parity and rollback-window checks. This compatibility read is local
runtime coordination only: it does not promote `.cache/local-state/` to durable
truth, does not replace `.ethos/profile.toml`, and does not let product code own
adopter-specific profiles or fixtures.

SQLite `.ethos/state/state.sqlite` remains the product-native local-state store;
when both SQLite and JSON projections contain the same branch, the SQLite lease
wins. Expired or malformed JSON projection leases are ignored. The JSON
projection exists so external ETHOS can be at least as strong as an adopter's
embedded backend while the adopter is still in migration.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).
