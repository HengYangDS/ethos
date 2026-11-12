# Tasks

## 1. Move OpenSpec

- [x] 1.1 Move `@fission-ai/openspec` to 2.0.0 in `package.json` and the npm lock, holding every
      other package to the 24-hour cutoff. Done when every resolved URL is the public registry, the
      lane's bootstrap installs it, and `ethos --version` reports OpenSpec 2.0.0. `f0505e280`
      changes one lock entry, `@fission-ai/openspec` 1.17.0 to 2.0.0, with the integrity the
      registry publishes; every resolved URL is `https://registry.npmjs.org/`, the lane's bootstrap
      installed 2.0.0, and `ethos --version` reports `OpenSpec 2.0.0`.
- [x] 1.2 Report OpenSpec's skill ownership through the configuration bridge and route the packages
      it owns in the skill portfolio. Done when a repository whose `.agents/skills/.openspec-target`
      names a tool passes the skills gate with an unregistered `openspec-propose` package, a package
      that the record keeps still reports `skill_package_unregistered`, the same package without the
      record reports it too, and the test fails before the change.
      `test_openspecs_record_routes_the_shared_skills_it_owns` failed first on its `claude` case
      with `skill_package_unregistered:openspec-propose`. With `f0505e280` its three cases passed,
      and the skills, OpenSpec adapter, version and OpenSpec lifecycle modules passed 396 tests with
      OpenSpec 2.0.0 installed. `115be540c` then moved the observation out of the portfolio, which
      the import contracts required: the test now runs the skills gate's provider through the gate
      runner, and the 22 impacted targets passed 1,131 tests.
- [x] 1.3 Rebuild the CI supply image from the moved lock and bind it. Done when the image run
      succeeds and `.config/ci/pipeline.cue` names its digest. Run 43174327163 built the image from
      `f0505e280` and published
      `sha256:b5bdfde2befd80d1f7d03121204e3ee023262eebeb04a726398d99179c099844`; `941d022bb` binds
      it in `.config/ci/pipeline.cue`, and the GitLab projection selects it.
- [x] 1.4 Record the move and the owner's exception in the Unreleased entry. Done when the entry
      names the version, the breaking `openspec update` step for older skill copies, and the
      exception's scope and exit. `f0505e280`'s Unreleased entry names OpenSpec 2.0.0 as breaking,
      the one `openspec update` for older skill or command copies, and the exception, which covers
      that package alone and lapses at 2026-11-12T22:41:44Z.

## 2. Acceptance

- [ ] 2.1 Pass the impacted tests, the precheck and readiness at the lane head. Done when each
      passes on the committed head.
