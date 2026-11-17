# Tasks

## 1. Environment owner

- [x] 1.1 Add the owner's tests in `tests/unit/ci/delivery/test_hermetic_journey.py`. Done when
      they fail before the owner exists and cover a child that inherits and one that is handed
      the environment, Git without host configuration or templates, the host's environment
      after the stage, and the removal of the environment's tree.
- [x] 1.2 Add `hermetic_environment` beside the minimal environment in
      `tools/ci/delivery/acceptance/host_environment.py`. Done when 1.1 passes and the
      decision-density baseline no longer pins the minimal environment's function.
- [x] 1.3 Add `hermetic_gap` with one test case for each way the environment can show more than
      it declared. Done when each case fails against a check that reports nothing, then passes.
- [x] 1.4 Show the place of the host's tool supply to the preparation of Mise alone. Done when
      a command inside it inherits the supply's place, a child after it sees none, a journey's
      downloads see none in their process, and each name is afterwards as it was, also when
      the preparation fails.
- [x] 1.5 Refuse, on a Windows stage, a declared executable that the minimal path does not
      hold. Done when the owner's test, with its view of the operating system replaced, reads
      the refusal by name, a path without an added directory and a named variable beyond the
      declaration. No run on Windows verifies it.

## 2. Acquisition

- [x] 2.1 Move the forge lookups, the class-bound verification, the pin's lock and install and
      the rebound locks to `tools/ci/delivery/acceptance/acquisition.py`. Done when the existing
      journey tests pass against the new module with no behavior changed.
- [x] 2.2 Write the manifest and read it strictly. Done when the reader's test refuses a manifest
      that is absent, unparsable, empty, partial, extended or that leaves its directory, each
      seen failing first.
- [x] 2.3 Hand the forge token to the forge's client and to Mise's pin calls. Done when the
      tests show the token as an argument of both and in no stage's process environment.
- [x] 2.4 Hold the token's test to every call that carries the key. Done when a call that
      carried an empty token would fail it, as it did before this Change.

## 3. Qualification

- [x] 3.1 Hash each acquired archive again before Mise installs it offline. Done when a changed
      archive refuses with `release_journey_archive_tampered:<archive>` and nothing is installed.
- [x] 3.2 Check the environment before the first child. Done when a reported gap stops the leg
      with `journey_environment_not_hermetic:<what>` after acquisition and before any install.
- [x] 3.3 Build each fixture adopter inside the stage's environment and resolve Mise inside
      acquisition's. Done when the fixture's commit verifies without a template directory, and a
      Mise on the host's path is not the one the installs receive.
- [x] 3.4 Record `venue` in the receipt. Done when the receipt test reads `ci` and `local`.
- [x] 3.5 Give Mise the manifest's digest as the archive's checksum. Done when the offline
      install's table carries the digest that its caller names, the archive's own without
      one, a given digest that is no SHA-256 is refused, and the journey's installs record
      their manifest's digest.
- [x] 3.6 Keep the venue's reading of `CI` equal to the product's other readers of that input.
      Done when an empty `CI` writes `local` and a set one `ci`.
- [x] 3.7 Place each stage's directories under the host's temporary directory, outside the
      checkout, and remove them when the journey ends. Done when the journey's test finds two
      stage roots, neither under the journey's work directory, and neither left afterwards.

## 4. Documents and budgets

- [x] 4.1 Add the changelog entry and the spec delta. Done when OpenSpec validates the Change
      strictly and Prettier and the documentation registry accept the documents.
- [x] 4.2 Measure the source budget. Done when the report states product, tests and tools, with
      tools by file.

## 5. Lane, hosted run and owner

- [x] 5.1 Apply the patch in the Work Lane and pass its pre-check and readiness. Done when both pass
      at the lane head. Both passed at `4a5029e96` on 2026-11-17: the pre-check with 472 impacted
      test modules (9,555 passed, 5 skipped, no finding) and readiness with its 28 gates.
- [x] 5.2 Read the Linux leg of the lane head's hosted run. Done when the two journey test modules
      pass there; they ran on macOS only during preparation. In run 43991840423 at `4a5029e96` both
      Linux suite legs pass `tests/unit/ci/delivery/test_hermetic_journey.py` (27 tests) and
      `tests/unit/ci/delivery/test_journey.py` (35 tests).
- [x] 5.3 Dispatch the journey alone for the newest published prerelease and its predecessors. Done
      when both legs' receipts read `passed`, name `venue` as `ci` and hold both refusals; record
      each leg's time beside the last run before this Change. Run 43992039510 at `4a5029e96` for
      `v0.2.0-beta.10` with `v0.2.0-beta.9` before it: each receipt reads `passed` with `venue` `ci`
      and holds both refusals. The legs took 261 s on Linux x64 and 254 s on macOS, where the last
      run before this Change (43542619629) took 633 s and 1,140 s; the Linux ARM64 leg of
      `journey-hosts` took 271 s.
- [x] 5.4 Decide whether the releasing host runs the journey as a local venue. Done when one local
      receipt reads `passed`, or the reason it cannot run there is recorded. One local run on
      2026-11-17 at the lane head, under a host ticket: its receipt names `venue` `local` and reads
      `failed` with `release_journey_release_lookup_failed`. The journey reads its forge token from
      `GH_TOKEN` alone, and the releasing host's client is signed in through its own store, which
      acquisition's fresh home does not hold. The host runs no local venue until the owner hands the
      journey a token for it.
- [x] 5.5 Give the committee the measured tools size for its decision on the release rehearsal. Done
      when the weekly page states it by file. Stated in the weekly page's hand-kept measures on
      2026-11-17, by file at `4a5029e96` against `dev`: +275.4 line-equivalents of tools in the
      batch, of which this Change's own commits are +242.1.

## Workflow follow-up

- Owner: a local venue needs a forge token in the journey's launch environment. Decide whether the
  releasing host gives it one for a run, or whether acquisition gains a way to use the host's own
  sign-in. Read again with `release-rehearsal`.
