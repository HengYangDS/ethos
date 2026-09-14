## Context

The current source imposes the same incorrect archive prerequisite in role
audits, mutation admission, land, accepted closeout, ref admission and proof
selection. Official OpenSpec supports both archive within a source review and
archive after merge. ETHOS's stricter assumption makes delivery-inclusive
Changes impossible to close honestly.

## Decisions

### Source Acceptance And Change Completion Are Different Claims

Source acceptance admits one exact Git object under current authority, required
quality proof and applicable intent. It does not assert that every task or
actual-use outcome is complete. The same official Change remains active while
those obligations are outstanding. Task updates are ordinary source changes;
they invalidate exact-HEAD evidence even when accepted meaning is unchanged.

Archive remains a deliberate native transformation after the Change's declared
obligations are complete. It preserves the compiled acceptance and binds its
effect. A source-only Change may still archive before integration; this is a
scope choice, not a universal order imposed on delivery-inclusive Changes.

### Proof Follows Exact Source Meaning

The existing proof admission owner selects `proof:execution` for the exact
commit/tree and required policy floor. Repository transitions validate the
carried acceptance against the official source at that commit, whether the
Change is active or its archive effect is attested. They do not require a live
authoring Lease after integration. A separate fresh decision still authorizes
each source/ref effect; proof never grants the holder that authority.

Current-lane authoring proof retains its Lease checks. Contradictory proof
bindings, changed source or policy, missing required checks, malformed intent,
unknown objects and unauthorized effects remain blocking.

### Observation Does Not Manufacture Residue

The OpenSpec observer reports active Changes in governed branch trees as facts.
Presence alone is neither stale state nor a warning. Candidate is a local
integration role, not a protected remote branch. Commands consume these facts
without a second role-specific prohibition. Completed active tasks can make
archive eligible; they do not invalidate the source object.

## Alternatives Rejected

- Prechecking delivery tasks would falsely claim an effect before it occurred.
- A second delivery ledger would split official progress authority.
- Filename exceptions or a skip-archive flag would preserve the incorrect rule.
- Treating any green proof as source acceptance would omit exact intent binding.

## Validation

Start with public RED cases for an incomplete delivery-inclusive Change:
candidate integration, accepted closeout and ref observation must not demand
archive. Exercise the same Change through real Git integration, task updates,
archive and subsequent source acceptance in an isolated repository. Retain
counterexamples for incomplete archive, stale proof, contradictory intent,
missing authority and unavailable Git observations. No test may precheck a
future delivery effect to create readiness.

## Migration

Remove superseded enforcement and its obsolete tests in the same source change;
replace them with observations and distinguishing acceptance cases. Keep the
historical archive readable. Existing accepted runtimes can accept this bounded
source-only repair through their established archive-first path; the repaired
public lifecycle is verified independently before its installation.

The canonical terminal plan continues to own the global delivery sequence and
remaining lifecycle, recovery, quality, structure and ecosystem work. This
Change does not introduce a parallel plan or declare those goals complete.
