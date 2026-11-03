# Tasks

## 1. Change root files

- [x] 1.1 Limit the cross-Change refusal to paths inside another Change's directory. Done when a
      selected Change's prewrite of `openspec/changes/README.md` passes, a file inside another
      active Change's directory still reports `openspec_change_path_mismatch`, and the new test
      failed before the fix. (`test_selected_change_writes_change_root_files` failed with that gap
      for the guide and passes; 317 cases in ten admission, selection and lifecycle modules pass.)
- [x] 1.2 Record the fix in the changelog. Done when the Unreleased section of `CHANGELOG.md` names
      it under Fixed. (It does.)

## 2. Specification

- [x] 2.1 Write the `repository-governance` delta. Done when strict validation and the cumulative
      archive simulation pass. (`openspec validate change-root-files --strict` is valid, and the
      simulated archive leaves all 12 specs strictly valid.)

## Workflow follow-up

- Before landing, the GitHub and GitLab runs of the proposal at the lane's last code commit pass.
