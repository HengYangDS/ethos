# Tasks

## 1. Supply move

- [ ] 1.1 Move Mise to 2026.11.8 with its lock. Done when the floor and the CI bootstrap name
      2026.11.8, the six digests equal the release's `SHASUMS256.txt`, the lock names uv 0.13.8,
      Vale 3.27.0 and the 20261110 archives of CPython 3.14.10, and `mise lock --dry-run` reports no
      change.
- [ ] 1.2 Move the npm pins and lock. Done when `npm ls` is clean and every `resolved` entry of the
      lock is the public registry.
- [ ] 1.3 Move the Python lock and the floors of the moved direct dependencies, holding
      `complexipy` below 9 by a resolver constraint. Done when `uv lock --check` passes for the root
      and the fixture project, an upgrade dry run reports no change and the dependency declaration
      check reports no gap.
- [ ] 1.4 Reformat the file that Prettier 3.10.1 changes. Done when the format check names no file.
- [ ] 1.5 Move the supply image's base to the uv 0.13.8 image by digest, then rebuild and bind the
      CI supply image. Done when the bound digest is in `.config/ci/pipeline.cue` and the CI
      projection check passes.
- [ ] 1.6 Add the Changed lines to the Unreleased section of `CHANGELOG.md`. Done when Prettier and
      Vale accept them.

## 2. Acceptance

- [ ] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head.
