## 1. Legacy Custody Evidence

- [x] 1.1 Obtain each custody owner's release or migration decision through its own thread; for an owner still undecided at the 2026-10-23 review, the user decides.
      Evidence: no owner chose release or migration through its thread; 019f3a1b, 019fa96d and 01a00063 reported no member releasable (Workflow follow-up). At the review the user decided that every remaining member stays with its owner, neither migrated nor released. The selected set then held 2,260 members, 709 of them open-predicate; the largest are the `ethos:native-handoff-and-caller-byte-readback` member (30.6 MiB) and 28 `agent:codex:ethos:semantic-observation` members (9.4 MiB). a225c731's own ten members (0.11 MiB) stay as well.
- [x] 1.2 With each migrating owner, move its member's files byte-exact into custody and record a bounded successor; verify every embedded digest and obtain the owner's acceptance of the preserved copy.
      Evidence: no owner migrates (1.1).
- [x] 1.3 Release each original only after its owner accepts the preserved copy; verify the selected set no longer carries its bytes.
      Evidence: no original is released (1.1); a fresh read stays under 2 s without that (4.1).

## 2. Lane Records

- [x] 2.1 Record in design.md which retired-lane records proof admission and proposal retirement select, by which keys, and the positive evidence that ends each.
- [x] 2.2 End those records by that evidence in the lifetime owner; verify one regression per reader and that the records stay while a reader cannot be observed.
- [x] 2.3 Verify the land, closeout, publish, retire and proposal-retirement journeys on a scratch copy of the real set with ended lane records removed.
      Evidence: on 2026-10-22 these journeys ran on the real set itself, which updates had pruned since 2.2: two landings with their closeouts and GitHub publications, the `v0.2.0-alpha.7` tag publication, two lane retirements and the GitHub retirement of `proposal/20261014-repository-paradigm` (DR-0013 landed in `3e45904e0`). That retirement recorded a deletion whose zero object made lifetime reachability unobservable, so later updates ended no member (`attestation_lifetime_reachability_unavailable`). This change counts a deletion as selecting no commit (`test_a_deletion_publication_selects_no_commit`); with it the real set's facts are observable again, and an update ends its one superseded publication.
- [x] 2.4 Close an effect by any later attested reversal of its refs, not only the exact inverse, so a retired lane's start no longer blocks the same name at the same head (`git_effect_attestation_content_mismatch`, web-ingestion-benchmark 2026-10-18); verify the executor, lane-birth and lane-start regressions and that an unattested or forged reversal still blocks.
- [x] 2.5 Keep each superseded head's acceptance record as lineage provenance for historical maintenance bases while its proof, integration and publication records still end; verify a maintenance lane started from an earlier accepted base selects and fully validates the original accepted-effect record and still needs current proof, signatures, actor and Lease admission.
      Evidence: signed Git `86b98c47d` (`tests/unit/kernel/attestation_set/test_lifetime.py`).

## 3. Writer Gaps

- [x] 3.1 Make every reported writer gap recover without caller action: the next swap under the custody lock deletes stored bytes the new set does not bind, and `attestation record` projects the writer's gaps; verify that bytes a failed cleanup left are deleted by the next custody update.
- [x] 3.2 Delete the custody bytes an update stored when it exhausts its exact-CAS retries; verify that no unbound bytes remain and that the update still fails with `attestation_set_cas_retry_exhausted`.
- [x] 3.3 Report an existing oversized member as unchanged in `attestation record`; verify an unchanged root and the refusal of a new oversized member.

## 4. Reuse Removal

- [x] 4.1 Remove proof-throughput 2.15's in-process member reuse once a fresh process reads the selected set in under 2 s; keep file-backed native output capture and report the first-read time in the commit that checks this task.
      Evidence: five fresh processes read the 2,084-member real set in 1.667, 1.556, 1.588, 1.620 and 1.904 s, and three reads in one process took 2.04, 2.11 and 2.15 s under a higher load average, so the bound holds for a fresh read and a repeat read now costs what a first read costs. File-backed native output capture is unchanged, and the adapters spec still allows a reader to reuse validation.

## Workflow follow-up

- Each landing needs its own exact-head full proof, closeout and publication to both peers.
- Custody owners: `agent:codex:ethos:semantic-observation`, Codex threads 019f3a1b, 019fa96d, 01a00063 and 01a11a05, and the verifier of `evidence:historical-lane-preservation`. Pause notices were queued on 2026-10-15 with the user's authorization; 019f3a1b, 019fa96d and 01a00063 paused new embedding and reported no member releasable yet. Release-availability notices were queued to all four threads on 2026-10-16 after bounded-attestation-set landed. Owner status that evening: the semantic-observation verifier and 01a11a05 moved eleven members into custody; members over 1 MiB remain with 019f3a1b, `ethos:native-handoff-and-caller-byte-readback`, semantic-observation, 019fa96d and the 01a00063 desktop thread.
- Owner a225c731 reviewed the undecided members with the user on 2026-10-23 (1.1).
