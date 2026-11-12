# Tasks

## 1. Move OpenSpec

- [ ] 1.1 Move `@fission-ai/openspec` to 2.0.0 in `package.json` and the npm lock, holding every
      other package to the 24-hour cutoff. Done when every resolved URL is the public registry, the
      lane's bootstrap installs it, and `ethos version` reports OpenSpec 2.0.0.
- [ ] 1.2 Report OpenSpec's skill ownership through the configuration bridge and route the packages
      it owns in the skill portfolio. Done when a repository whose `.agents/skills/.openspec-target`
      names a tool passes the skills gate with an unregistered `openspec-propose` package, a package
      that the record keeps still reports `skill_package_unregistered`, the same package without the
      record reports it too, and the test fails before the change.
- [ ] 1.3 Rebuild the CI supply image from the moved lock and bind it. Done when the image run
      succeeds and `.config/ci/pipeline.cue` names its digest.
- [ ] 1.4 Record the move and the owner's exception in the Unreleased entry. Done when the entry
      names the version, the breaking `openspec update` step for older skill copies, and the
      exception's scope and exit.

## 2. Acceptance

- [ ] 2.1 Pass the impacted tests, the precheck and readiness at the lane head. Done when each
      passes on the committed head.
