# Tasks

## 1. The repair

- [x] 1.1 Plan a tag only from its mapped commit or from the accepted head above it. Done when a
      parametrized case refuses an unborn checkout, a lane branch with its own commit and a head
      detached at the replaced commit with `release_retag_checkout_unrelated`, at the preview and
      at the apply, and a head detached at the mapped commit plans.
- [x] 1.2 Re-create two tags on different commits in one run from the accepted head. Done when one
      apply under the preview's plan digest leaves each tag peeled to its mapped commit and
      verified.
- [x] 1.3 Close the known defect `retag-preview-ready-on-unborn-checkout`. Done when its entry's
      state is closed; its `fixed_in` is filled by the release Change.

## 2. Verification

- [x] 2.1 Run the re-creation on a copy of a governed repository whose release tags a completed
      repair mapped. Done when the apply under the preview's plan digest passes from the accepted
      head, each tag peels to its mapped commit, and the effect record's input and freshness name
      the accepted head.
- [x] 2.2 Measure the source budget on the patch with the product's budget report. Done when the
      report states product and tests and the verdict stays clean under the ceilings in force.
      (The product's budget report at `6afdde8e0`: product 85,067 of 90,000, tests 114,996 of
      115,000, tools 9,120; verdict pass.)
