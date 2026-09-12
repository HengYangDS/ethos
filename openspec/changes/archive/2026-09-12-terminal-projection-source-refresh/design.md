## Context

See proposal.md for the failure and scope. The archived scenario clarifies that
an empty current proof scope does not reuse historical archive authority, while
an applicable non-empty scope keeps strict validation. This refines execution
at an existing proof boundary and does not change the graph's entities,
relations, authority or target claims.

## Decisions

1. Reconcile the canonical delta before refreshing the digest. The added
   scenario is consistent with the graph's current-fact proof semantics; no
   node, relation or visual copy change is required.
2. Replace the one stale digest with SHA-256 of the canonical file bytes.
   Preserve every other graph value and every declared source path. Disabling
   source validation would violate the existing quality requirement.
3. Use the official `skip_specs: true` metadata because requirements do not
   change. A synthetic spec delta would rewrite a source during archive and
   recreate the same drift. Archive must preserve canonical spec bytes.
4. Reuse the actual-source regression and existing stale, missing, uncommitted
   and native-drift cases. They exercise the real exporter and its failure
   boundary without introducing implementation-mirroring tests.

## Risks / Trade-offs

- A digest update could conceal semantic drift: review the exact canonical
  delta and preserve the existing graph invariants before changing the hash.
- A concurrent source update could stale the binding: check the digest again
  before committing, and bind proof to the resulting exact HEAD.
- Archive could invalidate evidence: recheck canonical bytes and run proof on
  the archived HEAD before integration.

## Verification And Rollback

Observe RED with the actual-source export test, refresh the digest after exact
prewrite admission, and run the full projection test module. Commit the bounded
change, execute the architecture gate and head-bound full proof, then use
official archive and re-prove its resulting HEAD. A governed revert restores
the previous graph binding if semantic reconciliation proves incorrect.
