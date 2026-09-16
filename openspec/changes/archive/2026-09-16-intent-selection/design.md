## Context

The default selector searches the newest first-parent merge over all history.
The reproduced new lane starts at an accepted archive commit, so that search
finds a merge belonging to its predecessor. Its active Change is classified as
incoming, selection returns no Change, and archive fallback claims the paths.
Read-only evidence already identifies the exact native lane.start effect.

## Goals / Non-Goals

Restore one current intent across prewrite, default/explicit plan and proof,
while preserving same-lane archived contribution identity and fresh Lease checks.
Do not add Lease fields, an intent registry, timestamp-based authority, a second
state machine, adopter configuration or a universal active-before-archive rule.

## Decisions

Use native lane.start Git-effect evidence at the existing selection owner to
bound the first-parent contribution search. Validate selected evidence with the
existing effect decoder/validator; use the ref's exact initial object and native
ancestry, not creation time alone. Boundaries outside the selected source history
cannot decide its intent. Missing historical evidence retains existing native
contribution behavior rather than inventing a mandatory new carrier.

Preserve explicit official Change selection. Audit and proof must not silently
substitute the implicit archived choice for that request. Trace any remaining
proof/source or Lease discrepancy with the real public command before changing
its owner; observed audit prose alone does not prove the execution plan is wrong.

Resolve proposed paths at current resolution before compiling material scope;
prewrite must not inherit the empty scope of a clean working tree. Proof admission
distinguishes a Work Lane query from a repository transition: authoring evidence
must bind the queried lane and its current Lease generation. Historical evidence
from another lane remains valid for its own query, never as a replacement for
the new lane's proof. Repository transition semantics remain independently bound
to exact source intent rather than the continued existence of the old Lease.

Share the two exact-source policy compilations within one proof query instead
of recompiling both for every candidate and again for floor selection. A fresh
query still reobserves membership, policy inputs, lane and Lease; no persistent
cache or cached authorization is introduced. A counted native regression guards
the reduction without treating wall-clock noise as acceptance.

## Verification

Execute the old lane's real declared checks before and after native archive;
start a new lane at the same commit and read prewrite/default plan. Reject the
old proof in the new lane before executing both default and explicit proof,
then verify each lane selects its own evidence. Keep same-lane archive,
competing intent, malformed provenance, missing evidence, historical queries
and uncommitted intent cases. Use focused tests and inexpensive checks before
one frozen proof; no full proof is implied by these fixture checks.

## Risks / Trade-offs

- Branch reuse and multiple starts: prefer an unambiguous ancestry boundary;
  conflicting valid records remain unresolved, never latest-timestamp wins.
- Historical recovery: creation evidence is a historical fact, not current
  authorization; every mutation still rechecks actor, Lease and exact refs.
- Query cost: select only matching lane-start records before full decoding;
  no persistent cache of authority.
