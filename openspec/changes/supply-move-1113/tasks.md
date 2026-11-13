# Tasks

## 1. Supply move

- [x] 1.1 Move Node.js and the Python lock under the cutoff. Done when the Mise configuration and
      lock name Node.js 26.13.1, `uv lock --upgrade` with the cutoff changes nothing more, and
      `uv lock --check` passes. Evidence: at the lock step, 2026-11-13T03:19:59Z with the cutoff
      2026-11-12T03:19:59Z, `mise lock node@26.13.1 python` moved Node.js to 26.13.1 in the
      configuration and lock and left the CPython entries as locked;
      `uv lock --upgrade --exclude-newer` moved `cyclopts` 5.4.1, `fastmcp` and `fastmcp-slim`
      4.1.8, `ty` 0.0.101 and `uncalled-for` 0.6.1, a plain `uv lock` dropped the persisted option,
      all in `46417024d`. At 12:30:50 the same upgrade run under the cutoff resolved no change and
      `uv lock --check` passed.
- [x] 1.2 Rebuild and bind the CI supply image on the uv 0.13.7 base. Done when the bound digest is
      in `.config/ci/pipeline.cue` and the CI projection check passes. Evidence: run 43358972643
      built the image from `46417024d` on the uv 0.13.7 base and pushed
      `sha256:4e6f6c132fd0045562a7b22c4c7632f435b71d672b67c662b3360407de17eb8b`; `0ff092e01` binds
      it with its source commit in `.config/ci/pipeline.cue`, the projection check read conforming
      at 12:28:49, and the supply-image currency and provider projection tests passed, 37 of 37, at
      12:29:22.
- [x] 1.3 Add the Security and Changed lines to the Unreleased section of `CHANGELOG.md`. Done when
      Prettier and Vale accept them. Evidence: Prettier and Vale accepted `CHANGELOG.md` when
      `46417024d` was committed at 11:25:05.

## 2. Acceptance

- [x] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. Evidence: the full precheck at `46417024d` found, at 12:05:27, only the two supply-image
      binding tests, which pass since the binding in `0ff092e01` (37 of 37 at 12:29:22); the delta
      precheck from `46417024d` passed at `cf71d0742` with no finding at 12:39:09; readiness at
      `cf71d0742` passed 28 gates with none failing at 12:36:55.
