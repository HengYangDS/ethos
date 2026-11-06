# Tasks

## 1. Identity check

- [x] 1.1 Specify the identity check with failing tests. Done when assembler tests fail for a leg
      built from another commit, a leg with another distribution version, and an invalid head. Six
      tests failed first on the missing check.
- [x] 1.2 Check each leg's `source_commit` and `distribution_version` in
      `tools/ci/delivery/release_assets.py`. Done when those tests and the existing release tests
      pass, and the assembler admits beta.3's real uploads with the beta.3 head and refuses them
      with another one. 264 delivery and CI tests pass. With beta.3's head the assembler admits the
      real uploads, byte-identical to the release; with `9e8755a77` it refuses.

## 2. Workflow

- [x] 2.1 Pass the release head to the assembler in `.config/ci/pipeline.cue`. Done when a
      projection test reads `--expect-head ${{ inputs.release_head }}` in the publish step and the
      projection conforms. The test passes, and the projection is applied.
