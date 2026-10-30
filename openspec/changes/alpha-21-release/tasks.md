# Tasks

## 1. Release Entry

- [ ] 1.1 Move the product version to 0.2.0-alpha.21 in `VERSION` and
      `distributions/npm/package.json`. Done when the lane's `ethos --version` reports
      0.2.0-alpha.21, the version tests pass unchanged and no lock changes.
- [ ] 1.2 Curate the `0.2.0-alpha.21` entry from the Unreleased notes, every user-visible product
      change since `v0.2.0-alpha.20` and the advisories that the release build's audit reports on
      the landed head. Done when the changelog validates with 0.2.0-alpha.21 as its release target
      (`changelog_errors` with target 0.2.0-alpha.21) and the entry names every advisory that audit
      reports.

## 2. Supply

- [ ] 2.1 Bind the supply image built from the landed `release-path-repairs` head in
      `.config/ci/pipeline.cue`, and regenerate `.gitlab-ci.yml` with `ethos lane project`. Done
      when the image's `input.sha256` matches the lane head's inputs and the projection check
      passes.

## Workflow follow-up

- Archive this Change, prove the archived head once, then land, close out, bootstrap and publish
  `dev` and `main` to GitHub and GitLab.
- When the landed head's hosted runs pass, the release owner creates the signed tag with
  `ethos land --release`, publishes it to both peers, dispatches the hosted release on GitHub,
  verifies the published assets, accepts the adopter path and relays the identities to the adopter
  owners.
