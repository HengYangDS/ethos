# Tasks

## 5. Process Lifetimes and Resource Recovery

- [ ] 5.6 Close supervisor-loss and Windows descendant recovery with native regressions.
  - [x] 5.6.1 Propagate caller interruption through parallel gate command ownership; verify native cancellation, preserved independent diagnostics, exact proof and installed-runtime behavior.
  - [x] 5.6.2 Keep a timed-out command's cleanup from failing on Darwin's unreaped zombies: once the leader has exited, wait within a bound until its process group is absent, and still raise for a lasting refusal or a signalable member. A `git ls-remote` timeout in `ethos publish` raised `PermissionError` from cleanup instead of returning its structured unavailable observation (`test_exited_group_waits_for_reaping_but_never_ignores_a_survivor`).
- [ ] 5.11 Close native bootstrap identity wiring and tool transport timeouts; retain failed output, reuse verified supply across disposable checkouts, scope offline flags to bootstrap, and qualify cold and warm hosted consumers without increasing the deadline.
- [ ] 5.12 Reproduce ignored durable-custody loss at retirement; consume existing artifact declarations to distinguish retained, active, foreign, unknown and proved disposable resources before deletion. Incident Attestation `944c76c7`; recovery custody `2ffa2686` preserves 19 originals and two console captures; supplier `d2e61dfcb` still needs exact proof and installed retirement acceptance; `historical_evidence_loss_unresolved` remains open.
  - [ ] 5.12.1 Preserve exact predecessor runtime and wheel through the existing shared-installation owner before local reclamation; bind cutover to the original selector CAS, verify failure/no-op/concurrency boundaries, then qualify package and real-adopter rollback custody.
    - [x] 5.12.1.1 Close predecessor custody, post-selector failure and exact-CAS compensation at the existing owners; qualify the signed minimal wheel, immutable runtime and isolated public upgrade/rollback/no-op with independent byte review. Live-adopter adoption and full-source proof remain open.
    - [x] 5.12.1.2 Deliver the qualified minimal package through the Publisher owner's public activation; verify exact prior-runtime/wheel custody and the original implicit prewrite without user retelling. Keep whole-source proof, release and host-store reclamation distinct.
- [ ] 5.13 Qualify exact producer/consumer scratch ownership under repeated normal, crash and kill cycles; preserve live/unknown roots and shared supply, then measure source-bound 24/48-hour count, byte, inode and cleanup bounds before claiming recurrence closed.

## Workflow follow-up

- Prove the exact head, archive this Change, prove the archived head, then land, close out and publish.
