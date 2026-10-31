# Tasks

## 1. Supply Binding

- [ ] 1.1 Bind the published supply digest through the CUE owner and regenerate the projections.
      Done when `lane project --check` reports the projections conforming and every GitLab supply
      job selects the new digest and none the previous one.

## 2. Release Entry

- [ ] 2.1 Fold the Unreleased notes into the `0.2.0-alpha.22` entry. Done when the changelog
      validates with 0.2.0-alpha.22 as its release target, the Unreleased section is empty, and the
      entry names every advisory that the release build's audit of the lane head reports.

## Workflow follow-up

- Archive this Change, prove the archived head once, then land, close out, bootstrap and publish
  `dev` and `main` to GitHub and GitLab.
- When the landed head's hosted runs pass, tag it with `ethos land --release`, publish the tag to
  both peers, dispatch the hosted release, verify the published assets, accept the adopter path and
  relay the identities to the adopter owners.
