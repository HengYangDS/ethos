## 1. Claims and Released Custody

- [x] 1.1 Refuse members above 1 MiB in the set writer and `attestation record` before any effect; verify `attestation_member_too_large` and an unchanged root.
- [x] 1.2 Store declared `custody:sha256:<digest>` evidence byte-exact in the Git-common custody store; verify readback, refusal of a missing or mismatched file, and an unchanged index, tracked tree and remote.
- [x] 1.3 Derive one lifetime for every product predicate and transition in one pure owner; verify one regression per lifetime and open-predicate treatment of unknown predicates.
- [x] 1.4 Add `ethos attestation release` for open-predicate members; verify verifier and reviewed-owner release by exact CAS, deletion of unbound custody bytes, and refusal for other actors and product lifetimes.

## 2. Lifetime-Bounded Members

- [x] 2.1 Remove ended members in the set writer's exact-CAS update; verify concurrent writers, the custody lock, kept lane records, superseded versus pinned heads, repair lineage, and retained release, runtime and starter lineage.
- [x] 2.2 Verify the public land, closeout, publish, retire, release catch-up, signature repair and starter journeys with historical members removed.

## 3. Existing Members

- [x] 3.4 Measure the selected set's size and cold read time before and after lifetimes; report both in the commit that checks this task (fresh-process first read: 82c60265, 3,342 members, 565.7 MiB, 16.5 s; a627dfac, 1,369 members, 421.4 MiB, 6.5–7.3 s).

## 4. Contract and Cleanup

- [x] 4.1 Update the product design contract's Attestation lifetime, evidence and historical-bytes statements.

## Workflow follow-up

- Each landing needs its own exact-head full proof, closeout and publication to both peers.
- Moved to Change `retained-attestation-members` (owner a225c731, next action landing it right after this archive, review 2026-10-23): the custody owners' release or migration decisions, byte-exact migration and release of the originals (formerly 3.1–3.3), removal of the in-process member reuse once a cold read takes under 2 s (formerly 4.2), lane records bounded by their consumers, and three deferred writer gaps.
- Custody owners: `agent:codex:ethos:semantic-observation`, Codex threads 019f3a1b, 019fa96d, 01a00063 and 01a11a05, and the verifier of `evidence:historical-lane-preservation`. Pause notices were queued on 2026-10-15 with the user's authorization; 019f3a1b, 019fa96d and 01a00063 paused new embedding and reported no member releasable yet. Release-availability notices were queued to 01a00063, 01a11a05, 019f3a1b and 019fa96d on 2026-10-16 after the landing.
