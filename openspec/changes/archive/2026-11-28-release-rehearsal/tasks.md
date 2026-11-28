# Tasks

## 1. The model and the generated workflow

- [x] 1.1 Pin, in `tests/architecture/ci/`, that the four release jobs generate the text they
      generate at the base, and the conditions, needs and permissions of the four rehearsal
      jobs. Done when the new tests fail on the unchanged workflow for the missing jobs alone.
      (`tests/architecture/ci/test_release_rehearsal.py`, 4 tests: with the workflow and the model
      of `cc76c2de2`, the commit before the rehearsal, all 4 fail, each on a `KeyError` for
      `rehearsal-platforms` or `rehearsal-journey`; at `bb2f14783` they pass.)
- [x] 1.2 Add `rehearse_head` to the model: the input, the head rule, the full tier, and the
      rule that a dispatch with another selecting input rehearses nothing. Done when the model
      compiles and is formatted, and the six tests that compare the old head rule, tier and
      aggregate text are updated and pass.
      (The model compiles; `test_hosted_economy.py`, `test_suite_legs.py`,
      `test_github_commit_scope.py` and `test_ci_provider_projections.py` pass at `bb2f14783`.)
- [x] 1.3 Declare a release leg's job once and generate `release-platforms` and
      `rehearsal-platforms` from it. Done when a test shows that the two jobs' steps differ only
      in the checkout and the two argument strings.
      (`test_a_rehearsal_leg_is_the_release_leg_but_for_its_source` passes at `bb2f14783`.)
- [x] 1.4 Add `rehearsal-assets` and the verdict job `release-rehearsal`. Done when a test
      refuses a rehearsal job with a permission beyond reading contents and attestations, or
      with an input expression in a step.
      (`test_a_rehearsal_reads_and_writes_nothing` passes at `bb2f14783`.)
- [x] 1.5 Generate `.github/workflows/ci.yml` from the model. Done when the projection check and
      the workflow validation pass and the second forge's pipeline is unchanged.
      (`ethos lane project --check` reads `conforming` at `bb2f14783`; readiness passed at
      `1af6179e5`, whose workflow `bb2f14783` changes in one flag name; the rehearsal's commit
      leaves `.gitlab-ci.yml` unchanged.)

## 2. The admission of a rehearsal build

- [x] 2.1 Test the admission in the delivery tests: a signed, untagged head with a valid entry
      is admitted; an untrusted head, a tagged version, an invalid entry, a dirty or stale
      checkout and a request with both marks are refused by name. Done when the cases fail for
      the missing mode.
      (`test_a_rehearsed_release_source_is_admitted_by_its_trusted_head_before_its_tag` and the five
      cases of `test_a_rehearsal_refuses_every_other_head`: with `tools/ci/delivery/pipeline.py` of
      `cc76c2de2` all 6 fail; at `bb2f14783` they pass, the request with both marks included.)
- [x] 2.2 Add `--rehearse` to the release request and the third admission to
      `tools/ci/delivery/pipeline.py`, and pass it from the `build` and `install_smoke` sessions.
      Done when 2.1 passes and the tests of the two existing admissions pass unchanged.
      (2.1 passes, and the signed-tag cases of `test_release_publication.py` pass at `bb2f14783`.)

## 3. The journey on the run's assembly

- [x] 3.1 Test acquisition from a directory that holds a leg's archive and the assembly's
      checksum file: a matching archive enters the manifest with the class `rehearsed`, and
      another digest is refused before any install. Done when the cases fail for the missing
      source.
      (`tests/unit/ci/delivery/test_rehearsal_journey.py`: with `acquisition.py` and `journey.py` of
      `cc76c2de2`, 12 of its 13 cases fail; the one that passes is the session's, which those files
      do not own; at `bb2f14783` all 13 pass.)
- [x] 3.2 Add the source to the journey and its session, and take the predecessors from the
      record at the head, or from the changelog when the head records none. Done when 3.1 passes,
      the receipt names the source of the set, and the published journey's tests pass unchanged.
      (`test_a_rehearsal_names_its_subject_and_its_predecessors_from_the_committed_head`, 4 cases,
      and the 35 cases of `test_journey.py` pass at `bb2f14783`.)
- [x] 3.3 Add `rehearsal-journey` to the model, upload only the small files from the assembly,
      and regenerate. Done when the model tests of group 1 pass with the job pinned on the three
      declared hosts.
      (`test_a_journey_leg_takes_its_own_archive_and_the_assembly_checksums` passes at `bb2f14783`;
      the hosted run of task 5.2 ran the three journey legs.)

## 4. Documents and budgets

- [x] 4.1 State the rehearsal dispatch in `docs/guides/release-and-publication.md`: on the
      release lane's proposal ref, after the lane's proof and before the landing, and again
      for a release head that moved. Add the changelog entry. Done when Prettier, the
      documentation registry and the carried-page tests pass.
- [x] 4.2 Restate the accepted scenario for a hosted release build so that it names the
      rehearsal's admission, once `release-acceptance` is archived. Done when
      `openspec validate release-rehearsal --strict` passes with that delta.
- [x] 4.3 Measure the source budget on the patch. Done when the report states product, tests
      and tools against the planned 0, 190 and 240 (measured 0, 340 and 104; the design says
      why the tests exceed the plan).

## 5. Lane and hosted run

- [x] 5.1 Lane: apply the patch, run `ethos lane project --check` and readiness, and hand the full
      proof to the landing. Done when both pass and the Workflow follow-up states that the full
      proof runs on the archived head and that its receipt is the landing's.
      (Projection `conforming` and readiness passed at `1af6179e5`; the Workflow follow-up below
      states the proof. The lane's full pre-check at `cb73eee88` failed only on the stale supply
      image that the next commit rebound, and left no pass.)
- [x] 5.2 Hosted run: dispatch the hosted workflow on a proposal ref with `rehearse_head` set to
      that ref's head, at a head whose committed version has no tag: the release head of the
      batch, or a scratch head that moves the version and is never landed. Done when
      `release-rehearsal` succeeds, or each failed leg is read and repaired and the dispatch is
      repeated. This is the Change's first end-to-end run; no task of groups 1 to 3 is ticked
      on its tests alone.
      (Run 46082739654 on a scratch head above `bb2f14783` that moves the version to 0.2.0-beta.13,
      on its own proposal ref, never landed: every rehearsal leg passed in its first attempt; one
      conformance leg, macOS on Python 3.14, failed on a hosted network timeout and passed when
      rerun alone, and `release-rehearsal` then succeeded, 2026-11-28 09:03.)
- [x] 5.3 Hosted run: dispatch once with `rehearse_head` set to another commit than the ref's
      head. Done when no rehearsal leg runs and `release-rehearsal` fails.
      (Run 46081585042 on the lane's ref at `1af6179e5` with `rehearse_head` set to `cb73eee88`:
      every rehearsal leg was skipped and `release-rehearsal` failed, 2026-11-28 07:16.)
- [x] 5.4 Read the first run's times. Done when the run's wall time and each leg's time are
      recorded for `release-time-budget`.
      (Run 46082739654, first attempt: 78 minutes from dispatch to the verdict. Build legs:
      linux-x64 12 min 48 s, linux-arm64 10 min 1 s, macos-arm64 13 min 4 s, windows-x64
      29 min 26 s, windows-arm64 68 min 0 s; assembly 29 s; journey legs: linux-x64 4 min 43 s,
      linux-arm64 4 min 9 s, macos-arm64 6 min 36 s. The assembly waited 56 minutes for the
      windows-arm64 leg after the last of the other three ended.)

## Workflow follow-up

- Release: the first release head after this Change is rehearsed before its tag, and its entry
  says so. A failed rehearsal returns the release to its lane.
- Landing: the full proof runs on the archived head, and its receipt is the landing's. The hosted
  runs of that head are read before the landing.
- Delivery: the forge variable that binds the commit trust is read on the proposal ref of the
  first dispatch; a rehearsal leg refuses without it.
- The restatement of the accepted scenario (task 4.2) waits for the archive of
  `release-acceptance`, which modifies the same requirement.
