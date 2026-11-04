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
- [x] 1.2 Move uv to 0.13.7 once Mise admits it, and keep every release younger than 24 hours out of
      the Python locks. Done when Mise locks it for every platform, the `uv>=` floors are 0.13.7,
      every locked version that differs from `dev` was published at least 24 hours before the move,
      `uv lock --check` passes for both locks and `mise install --locked` installs it. Mise locks uv
      0.13.7 for the lockfile's six platforms and both `uv>=` floors are 0.13.7. The locked versions
      that differ from `dev` are FastMCP and fastmcp-slim 4.1.6, ty 0.0.96 and uv 0.13.7, each on
      PyPI for at least 24 hours when `f50e4fc05` moved them; `uv lock --check` passes for both
      locks and `mise install --locked` installs them. ty, `dependencies`, `build`, `supply_chain`,
      `ci_templates` and `vulnerabilities` pass, and 877 tests of the MCP surface, publication, CI,
      native supply, Nox adoption and release pass, 1 skipped.
- [x] 1.3 Bind a supply image built from the moved locks. Done when the hosted `supply_image`
      workflow built and pushed it from this lane, `lane project --check` reports the projections
      conforming and every GitLab supply job selects its digest. The hosted `supply_image` dispatch
      of the proposal ref (run 41764447664) built and pushed the image from `f50e4fc05`;
      `lane project --check` reports the projections conforming, and all five GitLab supply
      references select digest `ff6df8ddcec2`, none the previous one.

## 2. Release Entry

- [x] 2.1 Move the product version to 0.2.0-alpha.29 in `VERSION` and
      `distributions/npm/package.json`. Done when the lane's `ethos --version` reports
      0.2.0-alpha.29 and the version tests pass unchanged. The lane's `ethos --version` reports
      0.2.0-alpha.29, `uv lock --check` passes, and 207 tests of the release, changelog,
      publication, journey and land release surfaces pass unchanged.
- [x] 2.2 Curate the `0.2.0-alpha.29` entry from the Unreleased notes and the advisories that the
      release build's audit reports on the lane head. Done when the changelog validates with
      0.2.0-alpha.29 as its release target, the Unreleased section is empty, and the entry names
      every advisory that audit reports. The changelog validates with 0.2.0-alpha.29 as its release
      target and an empty Unreleased section. The release build's audit on `f50e4fc05` passes and
      reports only npm 12.2.1's eight bundled findings, which the entry's Security section names.

## Workflow follow-up

- Archive this Change after the lane's other Changes, prove the archived head, publish its proposal
  and dispatch one manual run on the same proposal ref for Windows on Arm, then land, close out,
  bootstrap and publish `dev` and `main` to GitHub and GitLab.
- When the head's hosted runs pass on every platform, tag it with `ethos land --release`, publish
  the tag to both peers, dispatch the hosted release, verify the published assets and their
  attestations with `gh attestation verify`, confirm that the run's `release-journey` legs pass on
  macOS and Linux, and relay the identities to the adopter owners.
