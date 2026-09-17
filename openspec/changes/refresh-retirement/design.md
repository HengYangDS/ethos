## Context

Completed `lane.refresh` evidence already binds an exact previous tip, candidate
and output through a native rebase Attestation and a verified Git CAS. Archive
resolution consumes it but publication retirement does not. A verified effect
alone also does not prove that an arbitrary replay preserved every contribution.

## Decisions

Move the native rewrite validator to the existing Git commit semantic boundary.
Archive keeps its exact archived-tree preservation rule. Publication uses the
same validated edge and additionally checks contribution preservation: the old
proposal belongs to the input history, the output belongs to accepted history,
and native three-way composition of candidate plus the complete old contribution
produces exactly the output tree. A unique merge base is required for this bounded
check. The relation is evidence, not present mutation authority.

Execute composition in a caller-owned temporary bare repository. Read original
objects through alternates, exclude repository/global/system configuration and
custom hooks, disable lazy fetching, use an explicit process deadline, and clean
only that temporary root. Native conflicts or unavailable/unsupported observations
cannot authorize deletion. Do not infer semantic equivalence from patch-id.

Keep peer accepted absorption, closed review, exact old OID, per-peer fresh
admission, CAS, partial-result recovery and idempotent retirement unchanged.
Retain original Attestations; derive the relation for the observation rather than
create a rewrite graph, token, database or second lifecycle.

## Alternatives

An ancestry-only rule strands valid native rewrites. A patch-id rule loses base
and composition semantics. Copying the archive validator creates competing
owners. Accepting the receipt without comparing the resulting tree can hide a
lost contribution. Reimplementing merge semantics in Python is unnecessary.

## Validation And Limits

Use real public refresh and publication paths in isolated repositories. Preserve
the existing direct-ancestry, repaired-history, review, stale-peer, lost-ACK and
replay cases. Missing or invalid evidence, absent content, ambiguous bases,
conflicts and unavailable tools must leave refs unchanged. Verify SHA-1/SHA-256
where supported and byte-exact scratch cleanup. Consolidate repeated fixtures
and assertions without deleting distinct cases to stay below the existing budget.
This proves bounded native composition, not arbitrary custom merge drivers or
universal equivalence of every possible rebase history.
