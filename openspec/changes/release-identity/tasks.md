# Tasks

## 1. Identity binding and readers

- [x] 1.1 Add the bound form to `AcceptedReleaseIdentity`, its constructor checks and
      `checksum_bound_release`. Done when a bound identity's payload is version 3 with the checksum
      digest and every listed wheel and archive, a disagreeing or malformed file refuses with its
      gap, and `tests/unit/release/test_release_identity_admission.py` passes after failing first.
- [x] 1.2 Admit version 3 in the reader beside versions 1 and 2, and compare checksum digests in
      release admission. Done when a literal version 2 payload yields the identity it recorded, a
      malformed bound payload refuses with `accepted_release_attestation_invalid`, and two bound
      identities of one version with different files conflict.
- [x] 1.3 Give `materialize_explicit_release` the optional checksum file. Done when the transition
      binds before any effect, a wheel that the file does not list refuses with no stored package,
      and the cases without the file pass unchanged
      (`tests/unit/release/test_runtime_transition.py`).

## 2. Release run

- [x] 2.1 Add `SHA256SUMS` to the attestation subjects in `.config/ci/pipeline.cue` and regenerate
      the projections. Done when the projection check reports no drift, only the GitHub projection
      changed, and `tests/unit/ci/delivery/test_release_publication.py` asserts the subject and its
      place before release creation.

## 3. Documents

- [x] 3.1 Name the checksum file in `docs/governance/provenance-and-attestation.md` and add the
      CHANGELOG line. Done when the Markdown and prose gates pass on both files.

## 4. Lane tasks

- [x] 4.1 Apply on the lane head after the Change that edits `.config/ci/pipeline.cue` before this
      one, regenerate the projections there with `ethos lane project`, and measure the three source
      budgets. Done when the projection check passes and the measured deltas are recorded with their
      reason: +69.0 product, +77.5 tests and 0 tools against the plan's +60, +60 and 0. The product
      lines are the release admission module (+61.8) and the transition (+7.2), the test lines their
      two test modules; the estimate was 1.15 and 1.29 times too low, and no file is near the size
      ceiling.
- [x] 4.2 Register the three new gap codes when the gap registry of this batch lands. Done when its
      static test passes with `accepted_release_checksum_mismatch`,
      `accepted_release_checksums_invalid` and `accepted_release_artifacts_invalid` registered.
- [x] 4.3 Pass readiness and the precheck at the lane head. Done when each passes on the committed
      head.

## Workflow follow-up

- After the first release run that follows this Change, its release Change reads back that the
  attestation step lists `SHA256SUMS` among its subjects and that `gh attestation verify` passes
  for the published file.
