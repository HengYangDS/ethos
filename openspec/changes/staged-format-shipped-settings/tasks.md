# Tasks

## 1. Staged format

- [x] 1.1 Check staged Python with the shipped Ruff settings when the repository tracks no Ruff
      carrier. Done when pre-commit refuses an unformatted staged Python file and admits a
      formatted one in a repository without a carrier, a tracked carrier still selects its own
      settings, and the new refusal case failed before the fix.
      (`test_pre_commit_requires_only_selected_capabilities_to_prove_clean[absent-…]` failed with
      hook exit 0 and passes; its `absent-valid` and carrier cases pass.)
- [x] 1.2 Resolve the shipped input in one helper that the hook and `native_configurations` share.
      Done when both call `shipped_resource` and the format gate's tests still pass.
      (1,618 of 1,620 cases in 59 hook, format-gate, adoption and resource modules pass. The other
      two, a format-fix case and an adoption case, failed because lane files were edited during
      the run and pass when rerun alone.)
- [x] 1.3 Record the fix in the changelog and the configuration reference. Done when the Unreleased
      section of `CHANGELOG.md` names it under Fixed and `docs/reference/configuration.md` says
      which settings check a repository without a Ruff carrier. (The fourth Fixed entry, and the
      Ruff policy bullet of the configuration reference.)

## 2. Specification

- [x] 2.1 Write the `repository-paradigm` delta. Done when strict validation and the cumulative
      archive simulation pass. (Strict validation is valid, and archiving it after
      `tracked-deletion-admission` and `packed-ref-retirement` leaves all 12 specs strictly valid.)

## Workflow follow-up

- Before landing, the GitHub and GitLab runs of the proposal at the lane's last code commit pass.
