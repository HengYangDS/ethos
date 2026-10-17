## 1. Legacy Custody Evidence

- [ ] 1.1 Obtain each custody owner's release or migration decision through its own thread.
- [ ] 1.2 With each migrating owner, move its member's files byte-exact into custody and record a bounded successor; verify every embedded digest and obtain the owner's acceptance of the preserved copy.
- [ ] 1.3 Release each original only after its owner accepts the preserved copy; verify the selected set no longer carries its bytes.

## 2. Lane Records

- [x] 2.1 Record in design.md which retired-lane records proof admission and proposal retirement select, by which keys, and the positive evidence that ends each.
- [x] 2.2 End those records by that evidence in the lifetime owner; verify one regression per reader and that the records stay while a reader cannot be observed.
- [ ] 2.3 Verify the land, closeout, publish, retire and proposal-retirement journeys on a scratch copy of the real set with ended lane records removed.

## 3. Writer Gaps

- [x] 3.1 Make every reported writer gap recover without caller action: the next swap under the custody lock deletes stored bytes the new set does not bind, and `attestation record` projects the writer's gaps; verify that bytes a failed cleanup left are deleted by the next custody update.
- [x] 3.2 Delete the custody bytes an update stored when it exhausts its exact-CAS retries; verify that no unbound bytes remain and that the update still fails with `attestation_set_cas_retry_exhausted`.
- [x] 3.3 Report an existing oversized member as unchanged in `attestation record`; verify an unchanged root and the refusal of a new oversized member.

## 4. Reuse Removal

- [ ] 4.1 Remove proof-throughput 2.15's in-process member reuse once a fresh process reads the selected set in under 2 s; keep file-backed native output capture and report the first-read time in the commit that checks this task.

## Workflow follow-up

- Each landing needs its own exact-head full proof, closeout and publication to both peers.
- Custody owners: `agent:codex:ethos:semantic-observation`, Codex threads 019f3a1b, 019fa96d, 01a00063 and 01a11a05, and the verifier of `evidence:historical-lane-preservation`. Pause notices were queued on 2026-10-15 with the user's authorization; 019f3a1b, 019fa96d and 01a00063 paused new embedding and reported no member releasable yet. Release-availability notices were queued to all four threads on 2026-10-16 after bounded-attestation-set landed. Owner status that evening: the semantic-observation verifier and 01a11a05 moved eleven members into custody; members over 1 MiB remain with 019f3a1b, `ethos:native-handoff-and-caller-byte-readback`, semantic-observation, 019fa96d and the 01a00063 desktop thread.
- Owner a225c731, review 2026-10-23: if an owner has not decided by then, ask the user how to proceed with its members.
