# Tasks

## 1. The model and the generated workflow

- [x] 1.1 Pin the three journey legs, each with its runner, in
      `tests/architecture/ci/test_release_journey.py`. Done when the test fails on the unchanged
      workflow, which has two.
- [x] 1.2 Name the journey's hosts as a list in `.config/ci/pipeline.cue`. Done when the model
      compiles and is formatted.
- [x] 1.3 Generate `.github/workflows/ci.yml` from the model. Done when the projection check
      passes, the second forge's pipeline is unchanged, and 1.1 passes.

## 2. Documents and budgets

- [x] 2.1 Add the changelog entry and the distribution delta. Done when OpenSpec validates the
      Change strictly and Prettier and the documentation registry accept the documents.
- [x] 2.2 Measure the source budget. Done when the report states product, tests and tools.

## 3. Lane, hosted run and owner

- [x] 3.1 Apply the patch in the Work Lane, after the hermetic journey where the batch lands both,
      and pass its pre-check, readiness and `ethos lane project --check`. Done when all three pass
      at the lane head. All three passed at `4a5029e96` on 2026-11-17: the pre-check with 472
      impacted test modules (9,555 passed, 5 skipped, no finding), readiness with its 28 gates, and
      the projection check.
- [x] 3.2 Dispatch the journey alone on the lane's ref for the newest published prerelease. Done
      when the job `release journey linux-arm64` succeeds, its artifact
      `release-journey-linux-arm64` holds a receipt whose platform is `linux-arm64` and whose state
      is `passed`, and the two other legs pass as before. Run 43992039510 at `4a5029e96` for
      `v0.2.0-beta.10`: the job succeeded in 271 s, its receipt reads `linux-arm64` and `passed`,
      and the Linux x64 and macOS legs passed.
- [x] 3.3 Hand the release entry's line on the Linux arm64 journey to the release Change of this
      batch. Done when the Workflow follow-up names the item: the entry no longer lists the Linux
      arm64 journey among what the beta does not qualify, once the leg of task 3.2 has passed.

## Workflow follow-up

- Delivery: read the journey of the first release run after this Change. Its three legs pass, or
  the release entry names the host whose journey failed or was unavailable.
- Release: when the release Change of 0.2.0-beta.12 is opened, its tasks drop the Linux arm64
  journey from what the release entry says the beta does not qualify, on the evidence of the leg's
  first passed run.
