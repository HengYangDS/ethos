## 1. Claims and Released Custody

- [x] 1.1 Refuse members above 1 MiB in the set writer and `attestation record` before any effect; verify `attestation_member_too_large` and an unchanged root.
- [x] 1.2 Store declared `custody:sha256:<digest>` evidence byte-exact in the Git-common custody store; verify readback, refusal of a missing or mismatched file, and an unchanged index, tracked tree and remote.
- [x] 1.3 Derive one lifetime for every product predicate and transition in one pure owner; verify one regression per lifetime and open-predicate treatment of unknown predicates.
- [x] 1.4 Add `ethos attestation release` for open-predicate members; verify verifier and reviewed-owner release by exact CAS, deletion of unbound custody bytes, and refusal for other actors and product lifetimes.

## 2. Lifetime-Bounded Members

- [ ] 2.1 Remove ended members in the set writer's exact-CAS update; verify concurrent writers, retired versus live lanes, superseded versus current heads, and retained release, repair, runtime and starter lineage.
- [ ] 2.2 Verify the public land, closeout, publish, retire, release catch-up, signature repair and starter journeys with historical members removed.

## 3. Existing Members

- [ ] 3.1 Obtain each custody owner's release or migration decision through its own thread.
- [ ] 3.2 With each migrating owner, move its member's files byte-exact into custody and record a bounded successor; verify every embedded digest and obtain the owner's acceptance of the preserved copy.
- [ ] 3.3 Release each original only after its owner accepts the preserved copy; verify the selected set no longer carries its bytes.
- [ ] 3.4 Measure the selected set's size and cold read time before and after lifetimes; report both in the landing commit.

## 4. Contract and Cleanup

- [ ] 4.1 Update the product design contract's Attestation lifetime, evidence and historical-bytes statements.
- [ ] 4.2 Remove proof-throughput 2.15's in-process member reuse once a cold read of the bounded set takes under 2 s; keep file-backed native output capture.

## Workflow follow-up

- Each landing needs its own exact-head full proof, closeout and publication to both peers.
- Custody owners: `agent:codex:ethos:semantic-observation`, Codex threads 019f3a1b, 019fa96d, 01a00063 and 01a11a05, and the verifier of `evidence:historical-lane-preservation`. Pause notices were queued on 2026-10-15 with the user's authorization; 019f3a1b, 019fa96d and 01a00063 paused new embedding and reported no member releasable yet.
