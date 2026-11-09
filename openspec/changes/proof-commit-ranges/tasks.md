# Tasks

## 1. Gate

- [ ] 1.1 Validate the publication ranges in the proof. Done when provider tests show a commit that
      the candidate's verifier refuses failing the gate, a clean range passing with peers that
      share a tip judged once, an empty range passing, an unobserved branch reported as a note,
      every configured peer unobserved refused as `commit_ranges_unobserved`, an invalid
      declaration refused with its gap, a checkout without a peer remote passing as not applicable,
      and the gate declared in the registry, planned by the full proof and bound to `src/ethos/`.
- [ ] 1.2 Regenerate the CI projections if the registry is one of their inputs. Done when the
      `ci-projection` gate passes.

## 2. Acceptance

- [ ] 2.1 Pass the lane precheck, the impacted sweep and readiness at the committed head, and run
      `commit-ranges` there as host evidence. Done when each passes and the host report shows
      `applicable: true` with a judged target for each configured peer.
