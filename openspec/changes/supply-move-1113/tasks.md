# Tasks

## 1. Supply move

- [ ] 1.1 Move Node.js, the CPython build and the Python lock under the cutoff. Done when the Mise
      configuration and lock name Node.js 26.13.1 and the 20261110 CPython build,
      `uv lock --upgrade` with the cutoff changes nothing more, and `uv lock --check` passes.
- [ ] 1.2 Rebuild and bind the CI supply image on the uv 0.13.7 base. Done when the bound digest is
      in `.config/ci/pipeline.cue` and the CI projection check passes.
- [ ] 1.3 Add the Security and Changed lines to the Unreleased section of `CHANGELOG.md`. Done when
      Prettier and Vale accept them.

## 2. Acceptance

- [ ] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head.
