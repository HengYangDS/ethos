# Tasks

## 1. Assembler

- [x] 1.1 Specify the declared legs with failing tests. Done when the assembler's unit tests fail on
      four cases: an optional leg that uploaded nothing, left out with `leg_incomplete` and named in
      the notes with the adopter rule; a missing required leg; an artifact for an undeclared host;
      and invalid host lists. Seven tests failed first on the missing `required` argument and
      `declared_hosts`.
- [x] 1.2 Take `--required` and `--optional` in `tools/ci/delivery/release_assets.py`. Done when
      those tests and the existing publication and inventory tests pass. 42 release tests pass.

## 2. Workflow

- [x] 2.1 Declare `required` on each release leg in `.config/ci/pipeline.cue`, and derive the
      matrix's `continue-on-error` and the assembler's arguments from it. Done when a projection
      test that compares the rendered arguments and `continue-on-error` with the declaration passes,
      and the projection conforms. The test passes, 253 CI and delivery tests pass, and the CUE
      checks refuse an emulated required leg and an optional journey leg.
