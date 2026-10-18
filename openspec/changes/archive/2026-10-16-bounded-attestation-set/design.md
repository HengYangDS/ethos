## Context

See [proposal.md](proposal.md). Measured on the selected set at `35843bce0` on 2026-10-15:

| Members                                                   | Count     | Size     | Product reader                             |
| --------------------------------------------------------- | --------- | -------- | ------------------------------------------ |
| Evidence custody (`quality:observation`, `evidence:*`, …) | 35 large  | 413 MiB  | none                                       |
| `effect:git-ref-update`                                   | 1,537     | 75.5 MiB | lane, closeout, release and repair readers |
| `proof:execution`                                         | 818       | 45.9 MiB | proof admission                            |
| `publication:remote-effect`                               | 383       | 25.2 MiB | publication                                |
| Other effects and observations                            | about 480 | small    | idempotence and recovery readers           |

One read spent about 22 s receiving `git cat-file --batch` output through a pipe and 15 s validating
canonical JSON. Proof-throughput 2.15 moves bulk output to a file and reuses validated members
within one process, but every process still validates the whole set once. The 3,212 members below 1
MiB account for 11 s of that validation, so moving custody bytes alone is not enough.

Every product reader selects members for an in-flight transition or a small lineage:

| Reader                                                                         | Selects                                                  | Lifetime          |
| ------------------------------------------------------------------------------ | -------------------------------------------------------- | ----------------- |
| Proof admission, OpenSpec archive transition                                   | proof and archive records of the head being admitted     | head              |
| Lane Change selection, refresh provenance, merge recognition, lease resolution | records bound to a lane, live or retired                 | operation, window |
| Ref-effect idempotence and recovery                                            | the effect of one unfinished transition                  | operation, head   |
| Accepted provenance and maintenance bases                                      | exact acceptance of the selected head or historical base | lineage           |
| Release catch-up                                                               | `release.promote` of an existing tag                     | lineage           |
| Signature repair provenance                                                    | repair results while pre-repair objects remain           | lineage           |
| Runtime admission and retention                                                | accepted release identities of kept generations          | lineage           |
| Starter evolution                                                              | the single starter formation                             | lineage           |

No product reader selects the open custody predicates. Accepted provenance stops at the first
validated acceptance for the requested commit. Maintenance release can request a historical
accepted base, so earlier acceptance records remain lineage rather than current-head evidence.
Their embedded proof remains the original acceptance witness; no expired proof is reactivated.

## Goals / Non-Goals

**Goals:**

- Bound the selected set by in-flight work and small lineages, not by history.
- Give evidence files a carrier that releases bytes and never enters Git history or remotes.
- Keep exact-CAS updates, deterministic roots and fail-closed readers.

**Non-Goals:**

- Deduplicating plan copies inside live routine records; revisit only if live members stay large.
- An archive of ended members, an index by predicate, or changes to other carriers.

## Decisions

### Members are claims; files go to custody

A member's canonical bytes are bounded at 1 MiB, above today's largest routine member (640 KiB), so
only embedded files are refused. The bound applies when a member is added; existing members stay
readable until they are released or migrated.

### Custody is Git-common content-addressed files

Custody files live at `<git-common>/ethos/custody/sha256/<digest>` and are written through the
existing content-addressed writer, like runtime packages. Release deletes them at once.

Alternatives considered:

- Git blobs in the set tree or under per-item refs: deletion waits for garbage collection, every
  root rewrite carries the tree, and a ref namespace invites accidental publication.
- Forge artifacts: they need network access and credentials and do not serve local consumers.

### One pure owner derives lifetimes and every update applies them

Lifetimes derive from existing fields: predicate, transition, subject, relations and `valid_until`.
No field is added. The set writer evaluates them against the observed set and fresh ref facts on
every update and removes ended members in the same exact-CAS update.

A lifetime ends only on positive evidence: a superseding landing with no ref, fully peeled tag,
worktree HEAD or peer's latest publication selecting the head, absent pre-repair objects, an expired
window or an explicit release. A missing branch, tag or package is not evidence. Operation records
outlive their lane: proof admission resolves archived intent and proposal retirement resolves
refresh provenance through a retired lane's records. Version admission refuses rollback against
every accepted release identity, so runtime lineage never ends by observation. Historical
acceptance likewise remains maintenance-base provenance; a later train advance alone cannot end
that consumer relationship. When facts cannot be observed, the update removes nothing and reports
the gap.

Alternative considered: let each ending operation remove its own members. That spreads one rule over
many commands and misses members whose operation never runs again.

### Ended members are deleted, not archived

The set root is parentless, so a removed member becomes unreachable and Git prunes it. Git history,
signed commits and merge structure keep source history; Forge CI and release records keep hosted
history. The product design contract narrows "historical bytes remain recoverable" to source
history.

### Open predicates end only by explicit release

ETHOS cannot evaluate the prose release conditions that custody members declare. Their verifier
releases them, or another actor does so with reviewed content and a reason, in the same shape as
reviewed lane abandonment.

### The temporary in-process reuse is removed after the set is bounded

Proof-throughput 2.15 reuses validated members within a process to unblock proofs. Once a cold read
of the bounded set takes under 2 s, that reuse adds state without benefit and is removed.
File-backed native output capture stays: it repairs a general transport defect.

## Risks / Trade-offs

- [A member that a reader still needs is classified as ended] → Ending needs positive evidence. The
  land, closeout, publish, retire, release catch-up, repair and starter journeys are verified after
  historical members leave, and a missing member fails closed with the reader's existing gap.
- [Accepted lineage grows with actual accepted commits] → Necessary provenance for historical
  maintenance bases remains. Superseded standalone proofs, candidate integrations and publication
  observations still shrink independently; an acceptance witness does not authorize a fresh effect.
- [Foreign evidence] → Custody members change only through their owners' decisions; bytes move
  byte-exact and are verified before release.
- [A concurrent writer binds a digest that a release is deleting] → One Git-common custody lock
  covers storing bytes through the swap and the swap through deletion, so a record waits for an
  in-flight deletion and then stores its bytes again. Cleanup after a swap is reported, never raised
  as a failed update.
- [Lane records accumulate] → They are small (943 members, about 6 MiB on 2026-10-16) but grow with
  every lane. Bounding them needs consumer-indexed lifetimes and is left to a follow-up Change.
- [A head record is needed after nothing selects its head] → Integration proves the lane head,
  acceptance and lane retirement read the accepted head, and publication proves the pushed head or
  tag commit, so each admission selects its head through a ref, tag or worktree HEAD. Landing a
  commit again after every ref that selected it was deleted needs a fresh proof.

## Migration Plan

1. Land custody, the size bound, release and lifetimes in one landing. Lifetimes never touch
   open-predicate members, so foreign custody evidence stays until its owner releases it. The
   landing's own proof is the first update by the new code, so record the selected root just
   before that proof starts: the set ref is local, Git keeps no reflog for it, and a replaced root
   stays readable only until Git prunes it.
2. Obtain each custody owner's decision, then migrate or release their members.
3. Measure size and cold read time, update the product design contract and remove the temporary
   reuse.

Step 2 and the reuse removal in step 3 wait on custody owners and continue in Change
`retained-attestation-members`, together with lane records bounded by their consumers.

Rollback reverts the landing and records the members of the recorded root again until Git prunes
it.
