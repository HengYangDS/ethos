# Tasks

## 1. The model and the generated workflow

- [ ] 1.1 Pin, in `tests/architecture/ci/`, that the four release jobs generate the text they
      generate at the base, and the conditions, needs and permissions of the four rehearsal
      jobs. Done when the new tests fail on the unchanged workflow for the missing jobs alone.
- [ ] 1.2 Add `rehearse_head` to the model: the input, the head rule, the full tier, and the
      rule that a dispatch with another selecting input rehearses nothing. Done when the model
      compiles and is formatted, and the six tests that compare the old head rule, tier and
      aggregate text are updated and pass.
- [ ] 1.3 Declare a release leg's job once and generate `release-platforms` and
      `rehearsal-platforms` from it. Done when a test shows that the two jobs' steps differ only
      in the checkout and the two argument strings.
- [ ] 1.4 Add `rehearsal-assets` and the verdict job `release-rehearsal`. Done when a test
      refuses a rehearsal job with a permission beyond reading contents and attestations, or
      with an input expression in a step.
- [ ] 1.5 Generate `.github/workflows/ci.yml` from the model. Done when the projection check and
      the workflow validation pass and the second forge's pipeline is unchanged.

## 2. The admission of a rehearsal build

- [ ] 2.1 Test the admission in the delivery tests: a signed, untagged head with a valid entry
      is admitted; an untrusted head, a tagged version, an invalid entry, a dirty or stale
      checkout and a request with both marks are refused by name. Done when the cases fail for
      the missing mode.
- [ ] 2.2 Add `--rehearse` to the release request and the third admission to
      `tools/ci/delivery/pipeline.py`, and pass it from the `build` and `install_smoke` sessions.
      Done when 2.1 passes and the tests of the two existing admissions pass unchanged.

## 3. The journey on the run's assembly

- [ ] 3.1 Test acquisition from a directory that holds a leg's archive and the assembly's
      checksum file: a matching archive enters the manifest with the class `rehearsed`, and
      another digest is refused before any install. Done when the cases fail for the missing
      source.
- [ ] 3.2 Add the source to the journey and its session, and take the predecessors from the
      record at the head, or from the changelog when the head records none. Done when 3.1 passes,
      the receipt names the source of the set, and the published journey's tests pass unchanged.
- [ ] 3.3 Add `rehearsal-journey` to the model, upload only the small files from the assembly,
      and regenerate. Done when the model tests of group 1 pass with the job pinned on the three
      declared hosts.

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

- [ ] 5.1 Lane: apply the patch, run `ethos lane project --check`, the pre-check, readiness and
      the full proof at the committed head. Done when each passes.
- [ ] 5.2 Hosted run: dispatch the hosted workflow on a proposal ref with `rehearse_head` set to
      that ref's head, at a head whose committed version has no tag: the release head of the
      batch, or a scratch head that moves the version and is never landed. Done when
      `release-rehearsal` succeeds, or each failed leg is read and repaired and the dispatch is
      repeated. This is the Change's first end-to-end run; no task of groups 1 to 3 is ticked
      on its tests alone.
- [ ] 5.3 Hosted run: dispatch once with `rehearse_head` set to another commit than the ref's
      head. Done when no rehearsal leg runs and `release-rehearsal` fails.
- [ ] 5.4 Read the first run's times. Done when the run's wall time and each leg's time are
      recorded for `release-time-budget`.

## Workflow follow-up

- Release: the first release head after this Change is rehearsed before its tag, and its entry
  says so. A failed rehearsal returns the release to its lane.
- Delivery: the forge variable that binds the commit trust is read on the proposal ref of the
  first dispatch; a rehearsal leg refuses without it.
- The restatement of the accepted scenario (task 4.2) waits for the archive of
  `release-acceptance`, which modifies the same requirement.
