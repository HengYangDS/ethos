# Tasks

## 1. The operation

- [x] 1.1 Add the catalog entries `hook.bind-trust.preview` and `hook.bind-trust.apply` and their
      implementation row. Done when the catalog's static-rule test counts both and passes.
- [x] 1.2 Add `src/ethos/application/hook/commit_trust.py` and its test module. Done when the test
      module fails before the implementation exists and passes after it: each of the three inputs
      previews without a write and binds with `--apply`, no input reports `unbound`, and every
      refusal names its gap and leaves the configuration and the temporary root unchanged.

## 2. The pipeline and the private path

- [x] 2.1 Call the operation from `.config/ci/pipeline.cue` and regenerate both projections. Done
      when the projection tests pass and no projection names `tools.ci.toolchain.commit_trust`.
- [x] 2.2 Remove `tools/ci/toolchain/commit_trust.py`, the two helpers in
      `tools/ci/toolchain/environment.py` and their three tests. Done when no tracked file outside
      the archive names them and `tests/unit/ci/test_ci_bootstrap.py` passes.
- [x] 2.3 Name the moved material case among the host cases of `tools/ci/delivery/pipeline.py`,
      and add a test that every host case names a test that exists. Done when that test fails on
      the removed name and passes on the moved one. Found by the first hosted runs of `cfa46ccec`:
      `host_conformance` failed on both forges with `not found` for the removed test.

## 3. Documents

- [x] 3.1 Describe the operation in `docs/reference/command-plane.md` and add the Added line to the
      Unreleased section of `CHANGELOG.md`. Done when Prettier, Vale and codespell accept both.

## 4. Lane, hosted and owner tasks

- [ ] 4.1 Pass `ethos lane project --check`, the precheck and readiness at the lane head. Done when
      each passes on the committed head and the source budget shows the tools class below the lane
      base.
- [x] 4.2 Observe one hosted run of the proposal ref on each forge. Done when the bootstrap step
      binds trust through the operation and `commit policy` admits the pushed range. Evidence at
      `3d5365a65`: GitHub run 43637623388, steps `Bind operator commit trust` and
      `Admit pushed commit range`; the GitLab pipeline of the same ref, whose commit policy job
      prints `bound` and then `admitted`.
- [x] 4.3 Run the material case on a Windows host. Done when
      `test_bound_material_is_protected_under_a_shared_temporary_root` passes there. Evidence:
      GitHub run 43642339317 at `3d5365a65`, whose four Windows legs run the host cases with 18
      passed and 2 skipped against 16 and 4 on macOS; the case skips only off Windows.
