# Tasks

## 1. Proposal runs

- [x] 1.1 Leave the Windows on Arm host conformance out of a proposal push. Done when the projected
      `host-conformance` matrix includes the Windows on Arm entry for every event except a push of
      a proposal ref, the release legs are unchanged, `lane project --check` reports the
      projections conforming and the release-publication tests pass. The projected `include` is
      a `fromJSON` expression on the proposal-push condition; the projections conform and 558 CI,
      projection and architecture tests pass.
- [x] 1.2 Name the move in the quality specification and the Unreleased notes. Done when the Change
      validates strictly and the changelog validates. The archive simulation of every lane Change
      validates all specifications strictly.
