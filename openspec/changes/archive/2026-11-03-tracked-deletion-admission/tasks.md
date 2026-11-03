# Tasks

## 1. Tracked deletions

- [x] 1.1 Classify an absent requested path that the index or HEAD tracks as a deletion in path
      mode. Done when prewrite of a tracked carrier the paradigm rejects, deleted from the worktree
      staged or unstaged, reports no paradigm gap, a new path at that location is still refused,
      and the new test failed before the fix.
      (`test_prewrite_admits_the_deletion_of_a_tracked_non_conforming_carrier` failed with
      `repository_paradigm_root_catalog:pytest.ini` in both cases and passes;
      `test_prewrite_refuses_a_new_path_the_paradigm_rejects` still refuses the new path.)
- [x] 1.2 Record the fix in the changelog. Done when the Unreleased section of `CHANGELOG.md` names
      it under Fixed. (The second Fixed entry.)

## 2. Specification

- [x] 2.1 Write the `repository-paradigm` delta. Done when strict validation and the cumulative
      archive simulation pass. (Strict validation is valid, and archiving it with
      `packed-ref-retirement` leaves all 12 specs strictly valid.)

## Workflow follow-up

- Before landing, the GitHub and GitLab runs of the proposal at the lane's last code commit pass.
