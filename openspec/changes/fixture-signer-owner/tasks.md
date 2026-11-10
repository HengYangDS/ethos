# Tasks

## 1. One signer owner and one session build

- [x] 1.1 Move every signer to `configure_fixture_signer` and delete the other two. Done when no
      test support creates a signer elsewhere, `/usr/bin/ssh-keygen` appears only as a mocked value,
      and the touched tests pass. e32acfa07 moves every signer to `configure_fixture_signer` and
      deletes `signature.configure_signer` and the inline keygen lines; the only
      `/usr/bin/ssh-keygen` left is a mocked `shutil.which` value; 212 touched tests and 292
      impacted tests passed.
- [x] 1.2 Resolve the invoking build once per worker. Done when fixture runtime installs resolve it
      at most once per worker and an `ethos` profile root keeps its own branch. Measured in a
      scratch clone at 5ab05f098: resolutions per install 2.000 before, 0.022 after (one per
      worker); an `ethos` profile root keeps `expected_runtime_build` (scratch branch check).

## 2. Acceptance

- [x] 2.1 Pass the precheck, the impacted sweep and readiness at the lane head. Done when each
      passes on the committed head. At b72198e5f: the precheck passed with 0 findings, the impacted
      tests (37 files) passed 292 with 1 skipped, and readiness passed 28 of 28 gates; the full
      suite runs in the proof.
