## Context

Lease CLI paths assembled transition rules procedurally, while linked landed and
superseded retirement had separate request types, effects, wrappers, and
compatibility projections. The terminal design needs one declaration-driven
reducer and one explicit destructive effect.

## Goals / Non-Goals

**Goals:**

- Compile renew, resume, handoff-offer, and handoff-accept generation
  transitions from the tracked workflow declaration through one pure reducer.
- Make one strict request model and one effect the only linked-retirement owner.
- Bind the effect to the exact current lease generation and accepted control
  state.
- Carry row expiry and raw payload digest through every lease, handoff, status,
  Chronicle, and receipt compare-and-swap boundary.
- Preserve the lane ref and lease whenever any observation or transaction
  boundary fails.
- Make Work Lane start reject pre-existing carriers and revoke a newly acquired
  lease only after exact carrier cleanup succeeds.
- Keep unavailable-holder retirement as an accepted policy mode over the same
  native revoke effect.
- Delete wrappers, re-exports, compatibility summaries, and redundant tests.
- Delete the archived source-budget Claim-specific rebase compatibility path.
- Delete every ignored SQLite lease migration and database-wide version claim.

**Non-Goals:**

- Do not add a DI container, event bus, workflow engine, graph framework, or
  compatibility shim.
- Do not implement the broader intent-continuity, takeover, or bounded-parallel
  design in this lifecycle transaction.
- Do not claim candidate landing, accepted closeout, remote publication, or
  hosted execution from this carrier.

## Decisions

1. **Declarations own generation-transition shape.** The workflow declaration
   defines the renew, resume, handoff-offer, and handoff-accept IDs, guards,
   states, and effect fields; CLI code supplies facts and dispatches only the
   declared effect. Acquisition and retirement remain separate lifecycle
   boundaries.
2. **One Pydantic request and one effect.** Landed and superseded remain CLI
   vocabulary only; both call the same semantic owner. Parallel public Python
   APIs are removed.
3. **SQLite generation lock owns lease mutation.** The effect begins
   `BEGIN IMMEDIATE`, verifies lease row/payload identity, holder, epoch, lane
   ref, expected head, and expiry, then stages exact-row deletion.
4. **Git owns worktree/ref mutation.** The effect rechecks control root,
   accepted HEAD, lane relation, checkout HEAD, and dirty state; removes the
   clean worktree; then verifies accepted ref and compare-and-deletes the lane
   ref through `git update-ref --stdin`.
5. **Compensation is narrow and no-clobber.** A failed SQLite commit rolls back
   the lease deletion and recreates the removed lane ref only if absent.
6. **Historical claims stay historical.** Earlier landed-summary, bounded
   retirement, and helper-location claims retain their original evidence and
   become superseded by this current carrier rather than being rewritten to
   prove stronger transactional semantics.
7. **Lease storage owns only its schema subset.** Ignored coordination state is
   disposable and the database is shared by orthogonal local-state owners. The
   lease runtime creates or validates only the exact current `leases` table and
   its unique subject index; it neither migrates retired lease shapes nor claims
   authority over unrelated tables or a database-wide version ledger.
8. **Storage owns subject uniqueness.** SQLite enforces one lease row per lane
   subject, so acquisition is one atomic insert and readers need no duplicate
   arbitration. Recorded v3 state is trusted only after full, non-partial
   structural uniqueness validation; every other lease shape fails closed and
   must be recreated through the current lifecycle.
9. **History does not execute.** Archived Claims and dated carrier paths remain
   evidence, not hard-coded runtime recovery rules. Generic parity and semantic
   ledger conflict resolution are the only replay mechanisms.
10. **Handoff consumes an immutable snapshot.** Import copies the complete,
    hash-verified package into private storage before any Git or Lease mutation,
    creates refs with no-clobber CAS, verifies ref/worktree/tree/Lease identity
    before acknowledgement, and deletes temporary refs only by expected value.
    Destination acknowledgement is a separate receipt and never mutates the
    content-addressed source package.
10. **One complete lease fingerprint crosses every boundary.** The exact
    generation comprises lease ID, holder, epoch, lane ref, expected head, row
    expiry, and raw payload SHA-256. Status, handoff, Chronicle, receipts, and
    effects must either carry all of it or fail closed; there is no five-field
    compatibility read.
11. **Policy modes do not own effects.** Ordinary holder relinquishment and
    accepted unavailable-holder recovery both call the same exact revoke
    primitive. The latter changes admission facts only; it does not introduce a
    wrapper, alias, or parallel storage effect.
12. **Lane start is a no-clobber saga.** Target path and ref absence are checked
    before and after lease acquisition. A failed Git add removes only an exact
    worktree/ref created at the leased expected head. Any uncertain ownership or
    cleanup failure retains the lease and observable carrier for deterministic
    recovery; only complete absence permits exact lease revocation.
13. **Cross-host handoff is actor-bound and content-addressed.** Import requires
    the invocation actor to equal the package target holder. A successful import
    emits a schema-validated acknowledgement whose content ID binds the package,
    target actor, lane/head, incarnation, and complete destination Lease
    generation. The acknowledgement is a destination-holder assertion, not a
    signature or remote authority proof.
14. **Content-addressed packages are immutable.** Re-export reuses an existing
    directory only when its manifest, declared artifacts, digests, and complete
    file set are identical; it never deletes or replaces that directory.
    Collision, invalid or extra prior content, and uncertain import compensation
    fail closed. Failed import revokes its exact new Lease only after its exact
    Git carriers are proven absent.

## Risks / Trade-offs

- **Git succeeds and SQLite commit fails** → roll back the lease and restore the
  exact lane ref create-if-absent.
- **Accepted ref moves during the effect** → the Git transaction blocks lane-ref
  deletion; lease deletion rolls back.
- **A test omits the committed reference-transaction hook** → the exact lease
  head is stale and retirement blocks; fixtures must model the real hook.
- **Temporary source growth** → accepted only inside this bounded Change; final
  wave and each later campaign wave must finish net-negative.
- **A target path or ref appears during start** → preserve it, retain or revoke
  only the newly acquired lease according to exact cleanup evidence, and never
  delete ownership-unknown state.
- **A cross-host acknowledgement is forged or edited** → its schema or content
  digest no longer matches, so source revocation blocks and the source Lease is
  retained.

## Migration Plan

1. Consolidate lease mutation, Work Lane start, and retirement; update exact
   race and compensation regressions.
2. Supersede overlapping historical claims without rewriting their Chronicles.
3. Run focused and full local quality gates at 100% line/branch coverage.
4. Archive this Change through the official OpenSpec lifecycle.
5. Commit, refresh from the current candidate through the official command,
   refresh Claim/parity evidence, execute HEAD-bound proof, and land locally.
6. Do not push until the terminal compression campaign closes.

## Open Questions

None for this bounded wave.
