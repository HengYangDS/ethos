## Context

This continuation separates tracked repository residue from ignored workstation
state. Tracked residue can be reviewed, tested, reverted, and landed through the
normal Work Lane lifecycle. Ignored `.ethos/state` data, recovery snapshots,
leases, and proofs require a separately authorized operator effect and cannot be
inferred from code, tests, OpenSpec archival, or Git movement.

The predecessor design also treated source-budget terminal settlement as part of
this change. Current policy uses `campaign_terminal`: campaign growth and an
unmet terminal target remain explicit advisories for a bounded Change, while an
invalid policy, debt-cap overflow, expired debt, or stale debt remains blocking.
This change observes that policy but does not own global compression completion.

## Goals / Non-Goals

**Goals:**

- remove tracked non-truth and dead projections while preserving active external
  runner and release policy;
- make Rules V2 migration lossless, guarded, and fail closed through the public
  command plane;
- implement and test versioned SQLite, conservative maintenance, archive
  verification, and proof-retention capabilities without applying them to real
  local state;
- retire bundled provider executables while preserving exact receipt semantics;
- retire non-authoritative performance evidence and cosmetic blank-line policy
  without weakening the hard quality floor;
- preserve historical claims unless this change records a bounded retirement;
- strengthen accepted-root closeout around exact candidate and control facts;
- complete strict validation, fresh parity, executed proof, candidate land, and
  accepted-root closeout on one final successor HEAD.

**Non-Goals:**

- mutating the real state database, leases, proofs, recovery snapshots, refs, or
  worktrees through maintenance code;
- creating an operator recovery archive or deleting its source material;
- claiming source-budget terminal settlement or changing budget policy;
- restoring compatibility wrappers, forwarding modules, aliases, or retired
  executable examples;
- treating local tests or local publication readiness as hosted or remote proof.

## Decisions

### 1. Tracked cleanup and adopter scaffolds change together

Product `.ethos` configuration and adopter templates remain one parity surface.
The root assistant file and dead release fields are removed from both sides. The
product keeps `[command_plane].public = "ethos"`, protected-ref policy,
publication remotes, and attestation policy.

### 2. Rules migration preserves policy and fails closed

Migration normalizes legacy rule keys while retaining every active non-rule
policy table. Dry-run is the default. Apply requires write admission,
authorization, expected HEAD, and compare-and-swap source binding. If a profile
assignment cannot be isolated safely, the public report returns a migration gap
and leaves the file byte-for-byte unchanged.

### 3. Local-state work is capability work, not a live effect

SQLite v2, lease inventory, proof retention, archive creation, extraction
verification, and replay behavior are tested with temporary repositories,
fixtures, and copied databases. No command in this continuation applies those
capabilities to the real accepted root or Work Lane state. OpenSpec archive,
land, and closeout receipts cannot substitute for an explicit maintenance apply
receipt.

### 4. Recovery material remains untouched

The code defines a preservation gate that requires entry hashes, archive digest,
extraction verification, and Git bundle verification before deletion. This
change does not create the real operator archive and therefore does not delete
any real recovery source.

### 5. Source-budget is observed, not settled here

The immutable baseline, terminal targets, category inventory, campaign binding,
and one unexpired debt record remain unchanged. At the recorded successor HEAD,
`quality source-budget` has no required gaps and reports campaign growth plus
terminal non-attainment as advisory. That result does not establish terminal
compression settlement. Existing blocking semantics for invalid, stale,
expired, or over-cap debt remain unchanged.

### 6. Provider contracts remain while bundled executables retire

Signed independent-verification, hosted-enforcement, external identity, and
control-replacement receipt contracts remain product behavior. Operator
executables do not. The active assurance claim is narrowed to the provider-
neutral contract. The generic pre-receive and physical-topology claims become
historical archived records because their bundled extension assets are retired.

### 7. Non-authoritative quality residue is deleted, not promoted

The same-machine performance evidence command, policy, Python owner, runner,
tool registration, and dedicated tests had no trust-bearing consumer and are
removed together. The custom structural blank-line reader is also retired.
Python lint, type, coverage, module layout, docstrings, configuration, shell,
format, repository hygiene, and other declared hard gates remain.

### 8. Historical claims require explicit disposition

The predecessor patch deleted 29 claim files without per-claim replacement or
retirement evidence. This successor restores them. Only the three independent-
verification claims receive explicit state or scope changes described above.

### 9. Closeout binds one exact candidate state

Control diff collection, external receipt admission, candidate proof, and
accepted-root mutation bind one observed candidate HEAD. An unavailable diff,
control deletion or rename, candidate drift, or candidate-local bootstrap
artifact blocks or defers closeout rather than being treated as success.

## Risks / Trade-offs

- **Rules text parsing may misidentify a table inside a multiline value.** The
  migration now converts that condition into a fail-closed public report and
  preserves the source file.
- **Provider retirement may erase active contracts.** Canonical receipt tests,
  docs, specs, and the active assurance claim remain; only executable examples
  and their current-product claims retire.
- **Historical claim deletion may look like cleanup.** Claims remain until a
  claim-specific transition proves otherwise.
- **Local-state code may be mistaken for an applied cleanup.** The Chronicle and
  claim state explicitly exclude real apply and deletion effects.
- **Source-budget advisories may be mistaken for completion.** Final evidence
  records exact metrics and `terminal_target_met=false` without attributing
  global settlement to this change.

## Migration Plan

1. Replay the predecessor semantic commits onto the current successor lane while
   preserving candidate-owned APIs and deleting stale parity evidence.
2. Restore unproven claim deletions and correct the three provider-related claim
   dispositions.
3. Reconcile proposal, design, tasks, deltas, canonical plans, Chronicle, and
   claim boundaries.
4. Validate focused owner suites, strict OpenSpec, claim digests, and the exact
   source-budget observation.
5. Use the official `lane refresh-base` command against the latest candidate;
   never hand-rebase or merge the Work Lane.
6. Regenerate generic parity only at the refreshed final HEAD and commit it.
7. Run the complete quality/test floor and HEAD-bound executed proof.
8. Archive the OpenSpec carrier, verify canonical-spec fusion, rerun proof on the
   archived HEAD, land to candidate, and perform accepted-root closeout.
9. Treat local publication readiness, remote publication, and hosted observation
   as distinct evidence classes.

Rollback for this change is Git revert of tracked changes. Real local-state
mutation has no rollback section here because no such effect is authorized or
performed by this change.

## Open Questions

None. Any later real maintenance apply or recovery archive is a separate,
explicitly authorized change.
