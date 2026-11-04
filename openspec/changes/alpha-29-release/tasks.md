# Tasks

## 1. Supply

- [x] 1.1 Move Syft and the Python lock to their latest stable releases through their owners'
      native resolvers. Done when `mise lock` locks Syft 1.56.0 for every platform of the lockfile,
      `uv lock --check` passes with the fastmcp and ty floors at the locked versions, the quality
      fixture's lock carries the root lock's version of every package they share, and the gates
      that run the moved tools pass. `uv lock --check` passes with 121 packages; ty, `dependencies`,
      `ci_templates`, `vulnerabilities`, `build` and `supply_chain` (Syft) pass, and 705 tests of the
      MCP surface, publication, CI and native supply pass. The hosted proof of `dfd394a9c`
      (run 41739758355) found the fixture still on coverage 7.17.0; locked to 7.17.1, the 31
      native Nox tests pass. Only uv 0.13.7 remains newer.
- [ ] 1.2 Move uv to 0.13.7 once Mise admits it. Done when Mise locks it for every platform, the
      `uv>=` floors are 0.13.7, `uv lock --check` passes and `mise install --locked` installs it.
- [ ] 1.3 Bind a supply image built from the moved locks. Done when the hosted `supply_image`
      workflow built and pushed it from this lane, `lane project --check` reports the projections
      conforming and every GitLab supply job selects its digest.

## 2. Release Entry

- [x] 2.1 Move the product version to 0.2.0-alpha.29 in `VERSION` and
      `distributions/npm/package.json`. Done when the lane's `ethos --version` reports
      0.2.0-alpha.29 and the version tests pass unchanged. The lane's `ethos --version` reports 0.2.0-alpha.29, `uv lock --check` passes, and 207 tests of the release, changelog, publication, journey and land release surfaces pass unchanged.
- [ ] 2.2 Curate the `0.2.0-alpha.29` entry from the Unreleased notes and the advisories that the
      release build's audit reports on the lane head. Done when the changelog validates with
      0.2.0-alpha.29 as its release target, the Unreleased section is empty, and the entry names
      every advisory that audit reports.

## Workflow follow-up

- Archive this Change after the lane's other Changes, prove the archived head, publish its proposal
  and dispatch one manual run on the same proposal ref for Windows on Arm, then land, close out,
  bootstrap and publish `dev` and `main` to GitHub and GitLab.
- When the head's hosted runs pass on every platform, tag it with `ethos land --release`, publish
  the tag to both peers, dispatch the hosted release, verify the published assets and their
  attestations with `gh attestation verify`, confirm that the run's `release-journey` legs pass on
  macOS and Linux, and relay the identities to the adopter owners.
