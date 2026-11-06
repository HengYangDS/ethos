# Tasks

## 1. Full-plan readiness

- [x] 1.1 Guard the refusal with a test that does not replace policy resolution. Done when the
      test runs the repository's real full policy and tier and fails against the selection-based
      run. The lane's real run refused first with `quality_obligation_unproven:behavior`. Against
      that implementation the test fails on its missing runner seam, not on the gap itself.
- [ ] 1.2 Run the tier's nodes from the full policy. Done when that test passes and the readiness
      run on the lane executes its tier.
