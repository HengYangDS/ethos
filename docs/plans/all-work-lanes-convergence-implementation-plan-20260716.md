---
subject: ethos:all-work-lanes-convergence-implementation-plan-20260716
role: plan
state: planned
relations:
  implements: all-work-lanes-convergence-program-20260716
  derives_from: repository-governance, archived-all-work-lanes-convergence-decision
---

# All Work Lanes Convergence — Implementation Plan

Purpose: sequence the governed local implementation and closeout of the exact
legacy Work Lane cohort while preserving foreign ownership and evidence bounds.

See also: [Convergence Program](all-work-lanes-convergence-program-20260716.md),
[Mutation Rules](../../rules/mutation.md), and
[Repository Governance Specification](../../openspec/specs/repository-governance/spec.md).

> **Execution contract:** use the owned carrier
> `<owned-governance-worktree>`; run exact
> prewrite before tracked writes; never edit a foreign Work Lane; never use
> `git stash`; preserve local closeout separately from remote publication.

## Phase 0 — Freeze and admit the carrier

1. Re-run `ethos orient --json`, `ethos status --json`, Git ref/worktree
   inventory, lease inventory, dirty digests, and process audit.
2. Merge the live snapshot with the graph/semantic audit; verify that the 36
   graph closeout candidates and 24 graph implementation refs are disjoint and
   cover the original 60 refs, and that 11 families cover the 24 implementation
   refs exactly once.
3. Record the hosted-observation dirty overlay separately because commit-graph
   classification cannot see it.
4. Create the program plan, this implementation plan, OpenSpec carrier,
   Chronicle, claim, and tracked inventory after exact prewrite.
5. Validate the carrier and commit the governance checkpoint.

## Phase 0.5 — Promote the governance decision first

1. Complete only the governance carrier checklist: exact cohort, classification,
   policy, plans, inventory, Chronicle, claim, and requirement delta.
2. Run strict OpenSpec lifecycle, claim validation, and plan; complete every
   pre-archive task and archive the carrier through official OpenSpec semantics.
3. Commit the archived carrier, refresh and commit generic parity evidence for
   that archived semantic tree, then obtain HEAD-bound executed proof for the
   final stable HEAD.
4. Land the proven governance HEAD to `candidate/dev`, perform sanctioned
   accepted-root closeout, and verify accepted/candidate equality and cleanliness.
5. Retire `work/all-lanes-convergence-20260716` through its holder-bound landed
   retirement path.
6. Start an owned successor implementation lane from the accepted governance
   HEAD. Bind its claim/scope to this accepted program. No exceptional legacy
   lane effect is allowed before this checkpoint is accepted.

## Phase 1 — Resolve valid foreign leases without impersonation

For `expert-review-remediation`, `hosted-observation-targets`, and
`npm-supply-governance`:

1. Re-observe holder, lease ID, epoch, expiry, HEAD, dirty digest, and concrete
   writer processes.
2. Prefer holder-bound proof/land/closeout. If the holder can cooperate, use the
   normal offer/accept handoff with explicit quiescence.
3. If handoff is unavailable, preserve the original lane read-only and replay
   its requirements in this owned carrier. Do not mutate the foreign lane.
4. Integrate only after focused tests and semantic review. Reclassify the
   remaining cohort after each accepted closeout.

## Phase 2 — Implement the 11 families

Each task uses the same loop: inspect current accepted behavior and all unique
lane commits; write or transplant the smallest missing test first; observe the
expected failure; implement the current contract; run focused and adjacent
checks; self-review; independent review; commit.

### Task 2.1 — OpenSpec lifecycle and scope

Branches: archive-transition scope admission, controlled-web-ingestion archive
scope closeout, new-capability lifecycle, prearchive task guard, and scope
recovery admission.

Required outcomes:

- archive transition preserves active-task and accepted obligation semantics;
- new capabilities and recovery scope are selected deterministically;
- stale carriers are not replayed wholesale; and
- strict official OpenSpec validation and lifecycle simulation pass.

### Task 2.2 — Container contract

Branches: provider-neutral recovery 2026-07-15 and source-budget compression.

Required outcomes:

- one provider-neutral container contract owns runtime/package boundaries;
- detached probes do not become a second product implementation; and
- the source budget is enforced after correctness, without hiding required
  semantics.

### Task 2.3 — Candidate and lane integrity

Branches: candidate generation lease, lane ledger integrity, and proof artifact
isolation.

Required outcomes:

- generation, holder, lease, epoch, expected-head, and claim bindings fail
  closed;
- proof artifacts remain same-HEAD projections rather than authority; and
- closeout/retirement remains crash-consistent and head-bound.

### Task 2.4 — Publication topology

Branches: dual-remote publication topology and dual-remote release topology.

Required outcomes:

- local readiness, GitLab, GitHub, and release distribution remain independent
  evidence planes;
- provider projections stay thin over repository-owned runners; and
- no remote success claim is introduced by this local program.

### Task 2.5 — Runtime evidence bundle

Branch: runtime-evidence-isolation.

Required outcomes:

- runtime evidence, semantic freshness, release topology, and quality policy are
  separated into their current owners;
- ignored runtime artifacts never become repository truth; and
- only the still-missing slices are replayed.

### Task 2.6 — Verification runtime

Branches: independent evidence verifier recovery and provider runtime verifier
continuation.

Required outcomes:

- execution-seat/broker boundaries and wheel/sdist runtime boundaries remain
  distinct;
- provider verification is source-bound and reproducible; and
- proof/publish receipts cannot overclaim hosted or remote execution.

### Task 2.7 — Quality and artifact policy

Branches: artifact hot-path repair, quality law, and zero-exception foundation.

Required outcomes:

- configured gates have one owner and no silent quality exceptions;
- hot paths are correct before performance claims; and
- generated artifact homes, coverage truth, and policy evidence remain
  consistent.

### Task 2.8 — Hosted runtime and supply

Branches: CI bootstrap runtime, npm supply governance, plus the dirty hosted
observation overlay.

Required outcomes:

- Python and Node/npm bootstraps are deterministic and source-bound;
- supplied npm prefixes/caches are isolated without a second package manager
  authority; and
- hosted evidence requires explicit configured provider observation targets.

### Task 2.9 — Governance foundations

Branches: principal delegation foundation and staged-secret admission.

Required outcomes:

- holder references never become a global principal/agent registry;
- delegation is policy-bound and exact-request scoped; and
- staged credential admission fails closed before execution.

### Task 2.10 — Documentation navigation

Branch: docs semantic navigation coverage.

Required outcomes:

- canonical entrypoints expose product, governance, rule, OpenSpec, and evidence
  surfaces without duplicating authority; and
- link/navigation checks cover the current tree rather than the stale branch
  snapshot.

### Task 2.11 — Expert remediation

Branch: expert-review-remediation.

Required outcomes:

- consume only the holder-completed or explicitly handed-off descendant;
- preserve target-root proof carry and armed-hook closeout behavior; and
- run the focused e2e tests before integration.

## Phase 3 — Successor proof and carrier archive

1. Re-run exact prewrite for every successor changed path and update the active
   implementation carrier scope.
2. Complete all implementation pre-archive checklist items and strict OpenSpec
   lifecycle validation.
3. Update the successor Chronicle commands/results and its bound claim digest.
4. Commit parity-relevant source, run `ethos parity gaps --json`, refresh generic
   shadow parity when stale, and commit that evidence.
5. Archive the active carrier through official OpenSpec semantics and commit the
   archive.
6. Run `ethos plan --changed --json` and HEAD-bound
   `ethos prove --execute --expect-head "$(git rev-parse HEAD)" --json`.
7. Any HEAD change after proof requires a new executed proof.

## Phase 4 — Candidate and accepted closeout

1. From the clean proven carrier, run `ethos land --json`, then the exact
   authorized apply command to fast-forward `candidate/dev`.
2. Re-audit candidate cleanliness and carried proof.
3. From a current runner, run accepted-root closeout dry-run, then
   `ethos land --closeout --apply --authorize --expect-head <old-dev>
   --root <accepted-root> --json`.
4. Verify `dev == candidate/dev == <proven-head>` and both protected worktrees
   are clean. Do not infer remote convergence.

## Phase 5 — Resolve and retire the frozen cohort

1. Promote the exact final resolution matrix into the accepted Chronicle before
   exceptional action.
2. For every missing-lease linked lane, create an exact fresh decision and apply
   it only if the observation digest still matches.
3. Dirty lanes use `preserve` or `preserve-retire`; verify bundle, tracked patch,
   untracked archive when present, manifest, and receipt before any deletion.
4. Clean absorbed lanes use holder-bound landed/superseded retirement when
   available; otherwise use accepted exceptional judgment.
5. Three unbound accepted ancestors use exact-head unbound retirement. The
   diverged unbound ref is integrated/preserved first; if the current product
   cannot produce a recoverable transition, record a blocking gap rather than
   raw-delete it.
6. Retire this governance carrier last.

## Phase 6 — Final audit

Freshly record:

- exact frozen refs remaining/absent;
- linked worktrees, unbound refs, and detached recovery worktrees;
- active/missing leases for the cohort;
- dirty paths and preservation receipts;
- accepted/candidate heads and cleanliness;
- strict OpenSpec, parity, proof, report, and local publish-readiness state;
- retained recovery-package inventory; and
- remote publication as not performed.

Report in the order: facts, evidence, unverified/blocked matters, next step.
