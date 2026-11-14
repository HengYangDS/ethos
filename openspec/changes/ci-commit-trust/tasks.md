# Tasks

## 1. The operation

- [ ] 1.1 Add the catalog entries `hook.bind-trust.preview` and `hook.bind-trust.apply` and their
      implementation row. Done when the catalog's static-rule test counts both and passes.
- [ ] 1.2 Add `src/ethos/application/hook/commit_trust.py` and its test module. Done when the test
      module fails before the implementation exists and passes after it: each of the three inputs
      previews without a write and binds with `--apply`, no input reports `unbound`, and every
      refusal names its gap and leaves the configuration and the temporary root unchanged.

## 2. The pipeline and the private path

- [ ] 2.1 Call the operation from `.config/ci/pipeline.cue` and regenerate both projections. Done
      when the projection tests pass and no projection names `tools.ci.toolchain.commit_trust`.
- [ ] 2.2 Remove `tools/ci/toolchain/commit_trust.py`, the two helpers in
      `tools/ci/toolchain/environment.py` and their three tests. Done when no tracked file outside
      the archive names them and `tests/unit/ci/test_ci_bootstrap.py` passes.

## 3. Documents

- [ ] 3.1 Describe the operation in `docs/reference/command-plane.md` and add the Added line to the
      Unreleased section of `CHANGELOG.md`. Done when Prettier, Vale and codespell accept both.

## 4. Lane, hosted and owner tasks

- [ ] 4.1 Pass `ethos lane project --check`, the precheck and readiness at the lane head. Done when
      each passes on the committed head and the source budget shows the tools class below the lane
      base.
- [ ] 4.2 Observe one hosted run of the proposal ref on each forge. Done when the bootstrap step
      binds trust through the operation and `commit policy` admits the pushed range.
- [ ] 4.3 Run the material case on a Windows host. Done when
      `test_bound_material_is_protected_under_a_shared_temporary_root` passes there.
