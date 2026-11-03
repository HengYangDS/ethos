# Tasks

## 1. Zero-to-zero deletions

- [x] 1.1 Govern a prepared zero-to-zero line for an existing ref as the deletion of its current
      value. Done when the protocol admits that deletion for an existing ref, keeps zero for an
      absent one, and the new test failed before the fix.
      (`test_a_zero_to_zero_deletion_is_governed_by_the_current_ref_value` failed with zero for the
      existing ref and passes.)
- [x] 1.2 Retire a packed absorbed ref under the generated hooks. Done when the absorbed-ref
      retirement of a packed ref applies, a deletion of the accepted branch without an old value is
      refused for a reason other than `ref_move_policy_unavailable`, and both failed before the fix.
      (`test_absorbed_ref_retires_exact_unbound_unleased_ancestor[hooked-packed]` and
      `test_accepted_branch_deletion_without_old_value_keeps_its_rules` failed with
      `ref_move_policy_unavailable` and pass; 373 of 374 cases in 15 admission, hook and retirement
      modules pass, and the other, a claim-matrix case, passes alone.)
- [x] 1.3 Record the fix in the changelog. Done when the Unreleased section of `CHANGELOG.md` names
      it under Fixed. (The third Fixed entry.)

## 2. Specification

- [x] 2.1 Write the `quality` delta. Done when strict validation and the cumulative archive
      simulation pass. (Strict validation is valid, and archiving it after
      `tracked-deletion-admission` leaves all 12 specs strictly valid.)

## Workflow follow-up

- Before landing, the GitHub and GitLab runs of the proposal at the lane's last code commit pass.
