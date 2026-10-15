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

| Reader                                                                         | Selects                                                   | Lifetime          |
| ------------------------------------------------------------------------------ | --------------------------------------------------------- | ----------------- |
| Proof admission, OpenSpec archive transition                                   | proof and archive records of the head being admitted      | head              |
| Lane Change selection, refresh provenance, merge recognition, lease resolution | records bound to a live lane                              | operation, window |
| Ref-effect idempotence and recovery                                            | the effect of one unfinished transition                   | operation, head   |
| Accepted provenance                                                            | the latest acceptance of the accepted head, repairs since | head              |
| Release catch-up                                                               | `release.promote` of an existing tag                      | lineage           |
| Signature repair provenance                                                    | repair results while pre-repair objects remain            | lineage           |
| Runtime admission and retention                                                | accepted release identities of kept generations           | lineage           |
| Starter evolution                                                              | the single starter formation                              | lineage           |

No product reader selects the open custody predicates. Accepted provenance stops at the first
validated acceptance, so it never reads older acceptances.

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

A lifetime ends only on positive evidence: a selected retirement effect, a superseding acceptance,
an absent tag or generation, an expired window or an explicit release. A missing branch is not
evidence, so a lane that is starting never loses its records.

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
- [ETHOS can no longer answer which proof admitted an old commit] → Accepted. Git signatures, merge
  structure, Forge CI and release records remain.
- [Foreign evidence] → Custody members change only through their owners' decisions; bytes move
  byte-exact and are verified before release.
- [A concurrent writer binds a digest that a release is deleting] → A record stores its supplied
  file before its CAS; a reader that finds a bound digest without bytes fails closed with
  `attestation_custody_missing`.

## Migration Plan

1. Land custody, the size bound and release, so new embedded files stop.
2. Obtain each custody owner's decision, then migrate or release their members.
3. Land lifetimes; the first update removes ended routine members. Its result names the replaced
   root, which stays recoverable by exact CAS until Git prunes unreachable objects.
4. Measure size and cold read time, update the product design contract and remove the temporary
   reuse.

Rollback before step 3 reverts the landing. After step 3, the replaced root can be selected again by
exact CAS until it is pruned.
