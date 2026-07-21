## 1. Contract

- [x] 1.1 Create the date-free logical Change and its dated episode trust Claim.
- [x] 1.2 Define one generation-bound linked-retirement requirement.

## 2. Consolidation

- [x] 2.1 Compile renew, resume, handoff-offer, and handoff-accept guards,
  states, and effects from the tracked workflow declaration through one
  reducer.
- [x] 2.2 Replace parallel landed and superseded request/effect APIs with one
  strict request model and one destructive owner.
- [x] 2.3 Remove the landed package, wrappers, thin forwarding, obsolete summary
  compatibility path, and redundant tests.
- [x] 2.4 Bind lease deletion, Git worktree removal, accepted-ref verification,
  lane-ref compare-and-delete, rollback, and no-clobber compensation.
- [x] 2.5 Remove every ignored SQLite lease migration, database-wide version
  claim, and compatibility test; accept only a fresh or exact-current lease
  schema subset while preserving unrelated shared-state owners.
- [x] 2.6 Remove the archived source-budget Claim-specific rebase resolver and
  dedicated regression file; retain only generic parity and semantic-ledger
  conflict resolution.
- [x] 2.7 Move one-lease-per-subject enforcement into SQLite and remove Python
  preflight/ambiguity duplication.
- [x] 2.8 Carry expiry and raw payload digest through every exact lease,
  handoff, Chronicle, and receipt boundary; remove the unavailable-holder
  effect wrapper.
- [x] 2.9 Make Work Lane start reject pre-existing carriers and retain the new
  lease unless exact failed-attempt cleanup fully succeeds.
- [x] 2.10 Bind cross-host import to the target actor, emit a content-addressed
  complete-generation acknowledgement, preserve immutable packages, and revoke
  an orphan destination Lease only after exact carrier cleanup.
- [x] 2.11 Snapshot verified handoff artifacts before use, publish packages and
  refs without replacement, and revalidate destination ref/worktree/tree/Lease
  identity before acknowledgement.

## 3. Verification and lifecycle

- [x] 3.1 Add exact holder/epoch/head, accepted-ref race, commit-failure
  compensation, and real committed-hook regressions.
- [ ] 3.2 Pass focused and full local product gates with Python warnings as
  errors and 100% line/branch coverage.
- [ ] 3.3 Complete zero-blocker correctness, governance, and ponytail reviews.
- [ ] 3.4 Validate the official archive preflight and record the post-archive
  transition boundary.

Archive, carrier relocation, commit, candidate-base refresh, parity refresh,
HEAD-bound proof, and local land are lifecycle transitions performed after all
task checkboxes are complete; they are not implementation tasks themselves.

The corpus-wide OpenSpec INFO findings and source-budget campaign advisories
remain blockers to campaign completion and are assigned to the immediately
following archive-identity normalization Change; they are not treated as
completed or suppressed by this carrier.
