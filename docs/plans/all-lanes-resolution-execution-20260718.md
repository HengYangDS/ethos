---
subject: ethos:all-work-lanes-resolution-execution-20260718
role: plan
state: archived
relations:
  implements: all-lanes-resolution-execution-20260718
  consumes: evidence/chronicle/all-work-lanes-convergence-20260716/2026-07-16.md
---

# All Work Lanes Resolution Execution — 2026-07-18

Status: archived after HEAD-bound proof; candidate and accepted-root closeout
remain pending.

Purpose: turn the fresh exact Work Lane inventory into portable, accepted,
preservation-first resolution decisions without inventing authority over foreign
holders or deleting unresolved work.

See also: [Mutation Rules](../../rules/mutation.md),
[Evidence Rules](../../rules/evidence.md), and
[All Work Lanes Resolution Chronicle](../../evidence/chronicle/all-lanes-resolution-execution-20260718/2026-07-18.md),
plus the [archived OpenSpec Change](../../openspec/changes/archive/2026-07-18-all-lanes-resolution-execution/).

## Objective

Convert the fresh exact Work Lane matrix into accepted, two-phase local
resolution decisions. Close only rows whose current Git evidence demonstrates
absorption; preserve dirty contents before any irreversible operation; and
record explicit blocks where semantic integration, a holder handoff, or a
separate authority boundary is still required.

## Ordered Execution

1. Archive this carrier only after its claim, matrix, and Chronicle validate.
2. Prove and land the policy carrier through candidate and sanctioned accepted
   closeout.
3. For every matrix row selected for `preserve`, run native
   `lane resolution decide` then `lane resolution apply`; verify its bundle,
   tracked patch, untracked archive when present, manifest, and receipt without
   deleting the branch or worktree.
4. Run `retire` or `preserve-retire` only if a fresh re-observation still selects
   that exact disposition. The current matrix selects neither.
5. Record native `block` outcomes for clean residual and holder-bound linked
   rows. Preserve the unbound ref as a content-addressed Git bundle before its
   non-destructive block record.
6. Re-observe all refs, worktrees, leases, resolution receipts, proof state,
   and publish readiness. Keep remote and hosted planes explicitly deferred.

## Non-Negotiable Boundaries

- Valid foreign leases stay holder-bound.
- A non-empty `git cherry` residual is not declared absorbed by branch age.
- Missing-lease dirty residuals are preserved by the resolver and retained for
  semantic replay; valid leased dirty overlays remain holder-blocked.
- Dirty work is never discarded manually.
- The 2026-07-16 frozen cohort and 2026-07-18 post-freeze rows remain separate
  matrix dimensions.
- Linked worktree locations are stored as a neutral token plus a SHA-256
  binding, so accepted evidence retains exact-observation identity without
  publishing workstation-specific paths.
