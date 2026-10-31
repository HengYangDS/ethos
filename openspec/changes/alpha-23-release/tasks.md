# Tasks

## 1. Release Entry

- [ ] 1.1 Move the product version to 0.2.0-alpha.23 in `VERSION` and
      `distributions/npm/package.json`. Done when the lane's `ethos --version` reports
      0.2.0-alpha.23, the version tests pass unchanged and no lock changes.
- [ ] 1.2 Curate the `0.2.0-alpha.23` entry from the Unreleased notes and the advisories that the
      release build's audit reports on the lane head. Done when the changelog validates with
      0.2.0-alpha.23 as its release target, the Unreleased section is empty, and the entry names
      every advisory that audit reports.

## 2. Supply Binding

- [ ] 2.1 Bind the published supply digest through the CUE owner and regenerate the projections.
      Done when `lane project --check` reports the projections conforming and every GitLab supply
      job selects the new digest and none the previous one.

## Workflow follow-up

- Archive this Change, prove the archived head once, then land, close out, bootstrap and publish
  `dev` and `main` to GitHub and GitLab.
- When the landed head's hosted runs pass, tag it with `ethos land --release`, publish the tag to
  both peers, dispatch the hosted release, verify the published assets, accept the adopter path and
  relay the identities and each repository's file list to the adopter owners.
